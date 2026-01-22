"""
GitHub app views - Dashboard, Fetch, Progress SSE.
"""

import json
import logging
import re
import time

from celery.result import AsyncResult
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .tasks import process_repositories

logger = logging.getLogger(__name__)

# Regex to match GitHub repo URLs
GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?(?:/.*)?$"
)


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Parse GitHub URL to extract owner and repo name."""
    url = url.strip()
    match = GITHUB_URL_PATTERN.match(url)
    if match:
        return match.group(1), match.group(2)
    return None


def extract_urls_from_excel(file) -> list[str]:
    """
    Extract GitHub URLs from uploaded Excel file.

    Expected format:
    - Column A (first column): GitHub slugs (e.g., "owner/repo")
    - Column B (second column): Taiga slugs (ignored for now)
    """
    import openpyxl

    urls = []
    workbook = openpyxl.load_workbook(file, read_only=True)

    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            # First column contains GitHub slugs
            cell = row[0] if row else None
            if cell and isinstance(cell, str):
                cell = cell.strip()
                if not cell:
                    continue

                # Check if it's already a full URL
                if "github.com" in cell.lower():
                    parsed = parse_github_url(cell)
                    if parsed:
                        owner, repo = parsed
                        full_url = f"https://github.com/{owner}/{repo}"
                        if full_url not in urls:
                            urls.append(full_url)
                # Otherwise treat as slug (owner/repo format)
                elif "/" in cell:
                    parts = cell.split("/")
                    if len(parts) == 2:
                        owner, repo = parts[0].strip(), parts[1].strip()
                        if owner and repo:
                            full_url = f"https://github.com/{owner}/{repo}"
                            if full_url not in urls:
                                urls.append(full_url)

    return urls


def extract_urls_from_text(text: str) -> list[str]:
    """
    Extract GitHub URLs from text input.

    Accepts both full URLs and slugs (owner/repo format).
    """
    urls = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line contains a GitHub URL
        if "github.com" in line.lower():
            parsed = parse_github_url(line)
            if parsed:
                owner, repo = parsed
                full_url = f"https://github.com/{owner}/{repo}"
                if full_url not in urls:
                    urls.append(full_url)
        # Otherwise treat as slug (owner/repo format)
        elif "/" in line:
            parts = line.split("/")
            if len(parts) == 2:
                owner, repo = parts[0].strip(), parts[1].strip()
                if owner and repo:
                    full_url = f"https://github.com/{owner}/{repo}"
                    if full_url not in urls:
                        urls.append(full_url)

    return urls


@login_required
def dashboard(request):
    """GitHub analytics dashboard."""
    from django.db.models import Count, Sum

    from .models import Commit, Issue, PullRequest, Repository

    repositories = (
        Repository.objects.filter(user=request.user)
        .prefetch_related("commits", "pull_requests", "issues")
        .order_by("-updated_at")[:20]
    )

    # Aggregate stats
    total_repos = Repository.objects.filter(user=request.user).count()
    total_commits = Commit.objects.filter(repository__user=request.user).count()
    total_prs = PullRequest.objects.filter(repository__user=request.user).count()
    total_issues = Issue.objects.filter(repository__user=request.user).count()

    context = {
        "repositories": repositories,
        "total_repos": total_repos,
        "total_commits": total_commits,
        "total_prs": total_prs,
        "total_issues": total_issues,
    }
    return render(request, "github/dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def fetch(request):
    """Handle Excel upload and start fetch task."""
    if request.method == "POST":
        urls = []
        error = None

        # Check for file upload
        if "file" in request.FILES:
            file = request.FILES["file"]
            if not file.name.endswith((".xlsx", ".xls")):
                error = "Please upload an Excel file (.xlsx or .xls)"
            else:
                try:
                    urls = extract_urls_from_excel(file)
                except Exception as e:
                    logger.exception("Failed to parse Excel file")
                    error = f"Failed to parse Excel file: {e}"

        # Check for text input
        elif "urls" in request.POST:
            text = request.POST.get("urls", "")
            urls = extract_urls_from_text(text)

        else:
            error = "Please provide an Excel file or paste GitHub URLs"

        if error:
            return JsonResponse({"success": False, "error": error}, status=400)

        if not urls:
            return JsonResponse(
                {"success": False, "error": "No valid GitHub URLs found"},
                status=400,
            )

        # Check for access token
        if not request.user.access_token:
            return JsonResponse(
                {"success": False, "error": "No GitHub access token. Please re-authenticate with GitHub."},
                status=401,
            )

        # Queue Celery task
        task = process_repositories.delay(request.user.id, urls)

        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "urls_count": len(urls),
            "urls": urls,
        })

    return render(request, "github/fetch.html")


@login_required
@require_GET
def fetch_progress(request, task_id: str):
    """SSE endpoint for real-time fetch progress."""

    def event_generator():
        """Generate SSE events from Celery task state."""
        result = AsyncResult(task_id)
        last_state = None
        last_meta = None

        while True:
            state = result.state
            meta = result.info if result.info else {}

            # Only send update if state changed
            if state != last_state or meta != last_meta:
                last_state = state
                last_meta = meta

                if state == "PENDING":
                    data = {"status": "pending", "message": "Task is queued..."}
                elif state == "STARTED":
                    data = {"status": "started", "message": "Task has started..."}
                elif state == "PROGRESS":
                    data = {
                        "status": "progress",
                        "current_repo": meta.get("current_repo"),
                        "stage": meta.get("stage"),
                        "detail": meta.get("detail"),
                        "progress_min": meta.get("progress_min", 0),
                        "progress_max": meta.get("progress_max", 100),
                        "repo_index": meta.get("repo_index", 0),
                        "repo_total": meta.get("repo_total", 0),
                        "overall_progress": meta.get("overall_progress", 0),
                    }
                elif state == "SUCCESS":
                    data = {
                        "status": "complete",
                        "result": result.result,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                elif state == "FAILURE":
                    data = {
                        "status": "error",
                        "error": str(result.result) if result.result else "Task failed",
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                else:
                    data = {"status": state.lower(), "message": f"Task state: {state}"}

                yield f"data: {json.dumps(data)}\n\n"

            # Poll every 500ms
            time.sleep(0.5)

    response = StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_GET
def task_status(request, task_id: str):
    """JSON endpoint for task status (polling alternative to SSE)."""
    result = AsyncResult(task_id)

    if result.state == "PENDING":
        response = {"status": "pending", "message": "Task is queued..."}
    elif result.state == "STARTED":
        response = {"status": "started", "message": "Task has started..."}
    elif result.state == "PROGRESS":
        meta = result.info or {}
        response = {
            "status": "progress",
            "current_repo": meta.get("current_repo"),
            "stage": meta.get("stage"),
            "detail": meta.get("detail"),
            "progress_min": meta.get("progress_min", 0),
            "progress_max": meta.get("progress_max", 100),
            "repo_index": meta.get("repo_index", 0),
            "repo_total": meta.get("repo_total", 0),
            "overall_progress": meta.get("overall_progress", 0),
        }
    elif result.state == "SUCCESS":
        response = {"status": "complete", "result": result.result}
    elif result.state == "FAILURE":
        response = {
            "status": "error",
            "error": str(result.result) if result.result else "Task failed",
        }
    else:
        response = {"status": result.state.lower()}

    return JsonResponse(response)


@login_required
@require_GET
def repository_detail(request, repo_id: int):
    """View repository details and stats."""
    from django.shortcuts import get_object_or_404

    from .models import Repository

    repository = get_object_or_404(Repository, id=repo_id, user=request.user)

    # Get stats
    commit_count = repository.commits.count()
    pr_count = repository.pull_requests.count()
    issue_count = repository.issues.count()
    collaborator_count = repository.repository_collaborators.count()

    context = {
        "repository": repository,
        "commit_count": commit_count,
        "pr_count": pr_count,
        "issue_count": issue_count,
        "collaborator_count": collaborator_count,
    }
    return render(request, "github/repository_detail.html", context)


@login_required
@require_GET
def repository_commits(request, repo_id: int):
    """View commits for a repository."""
    from django.shortcuts import get_object_or_404

    from .models import Repository

    repository = get_object_or_404(Repository, id=repo_id, user=request.user)
    commits = repository.commits.all()[:100]

    context = {
        "repository": repository,
        "commits": commits,
    }
    return render(request, "github/commits.html", context)


@login_required
@require_GET
def repository_prs(request, repo_id: int):
    """View pull requests for a repository."""
    from django.shortcuts import get_object_or_404

    from .models import Repository

    repository = get_object_or_404(Repository, id=repo_id, user=request.user)
    pull_requests = repository.pull_requests.all()

    context = {
        "repository": repository,
        "pull_requests": pull_requests,
    }
    return render(request, "github/pull_requests.html", context)


@login_required
@require_GET
def repository_issues(request, repo_id: int):
    """View issues for a repository."""
    from django.shortcuts import get_object_or_404

    from .models import Repository

    repository = get_object_or_404(Repository, id=repo_id, user=request.user)
    issues = repository.issues.all()

    context = {
        "repository": repository,
        "issues": issues,
    }
    return render(request, "github/issues.html", context)


@login_required
@require_GET
def repository_analysis(request, repo_id: int):
    """View code analysis for a repository."""
    from django.shortcuts import get_object_or_404

    from .models import Repository

    repository = get_object_or_404(Repository, id=repo_id, user=request.user)
    file_analyses = repository.file_analyses.all()[:50]

    context = {
        "repository": repository,
        "file_analyses": file_analyses,
    }
    return render(request, "github/analysis.html", context)
