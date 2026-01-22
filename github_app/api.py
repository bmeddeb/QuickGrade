"""
GitHub Dashboard API endpoints.
Returns JSON data for charts and tables.
"""

from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncWeek
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import CodeReview, Collaborator, Commit, Issue, PullRequest, Repository


@login_required
@require_GET
def api_repositories(request):
    """Get list of user's repositories."""
    repositories = Repository.objects.filter(user=request.user).values(
        "id", "name", "full_name", "owner", "fetch_status", "last_fetched_at"
    )
    return JsonResponse({"repositories": list(repositories)})


@login_required
@require_GET
def api_repository_stats(request, repo_id: int):
    """Get stats for a single repository."""
    try:
        repo = Repository.objects.get(id=repo_id, user=request.user)
    except Repository.DoesNotExist:
        return JsonResponse({"error": "Repository not found"}, status=404)

    stats = {
        "repository": {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "default_branch": repo.default_branch,
        },
        "counts": {
            "commits": repo.commits.count(),
            "pull_requests": repo.pull_requests.count(),
            "issues": repo.issues.count(),
            "collaborators": repo.repository_collaborators.count(),
            "branches": repo.branches.count(),
            "files_analyzed": repo.file_analyses.count(),
        },
        "pr_stats": {
            "open": repo.pull_requests.filter(state="open").count(),
            "merged": repo.pull_requests.filter(is_merged=True).count(),
            "closed": repo.pull_requests.filter(state="closed", is_merged=False).count(),
        },
        "issue_stats": {
            "open": repo.issues.filter(state="open").count(),
            "closed": repo.issues.filter(state="closed").count(),
        },
    }
    return JsonResponse(stats)


@login_required
@require_GET
def api_commits_over_time(request):
    """Get commits over time for charting."""
    repo_ids = request.GET.getlist("repo_id")
    days = int(request.GET.get("days", 90))
    group_by = request.GET.get("group_by", "day")  # day or week

    # Base queryset
    commits = Commit.objects.filter(repository__user=request.user)

    if repo_ids:
        commits = commits.filter(repository_id__in=repo_ids)

    # Date filter
    start_date = datetime.now() - timedelta(days=days)
    commits = commits.filter(authored_at__gte=start_date)

    # Group by date
    if group_by == "week":
        commits = commits.annotate(date=TruncWeek("authored_at"))
    else:
        commits = commits.annotate(date=TruncDate("authored_at"))

    data = (
        commits.values("date")
        .annotate(count=Count("id"), additions=Sum("additions"), deletions=Sum("deletions"))
        .order_by("date")
    )

    return JsonResponse({
        "labels": [d["date"].isoformat() if d["date"] else None for d in data],
        "commits": [d["count"] for d in data],
        "additions": [d["additions"] or 0 for d in data],
        "deletions": [d["deletions"] or 0 for d in data],
    })


@login_required
@require_GET
def api_commits_by_author(request):
    """Get commit counts by author for charting."""
    repo_ids = request.GET.getlist("repo_id")
    days = int(request.GET.get("days", 90))
    limit = int(request.GET.get("limit", 10))

    commits = Commit.objects.filter(repository__user=request.user)

    if repo_ids:
        commits = commits.filter(repository_id__in=repo_ids)

    start_date = datetime.now() - timedelta(days=days)
    commits = commits.filter(authored_at__gte=start_date)

    data = (
        commits.values("author_name")
        .annotate(
            count=Count("id"),
            additions=Sum("additions"),
            deletions=Sum("deletions"),
        )
        .order_by("-count")[:limit]
    )

    return JsonResponse({
        "labels": [d["author_name"] for d in data],
        "commits": [d["count"] for d in data],
        "additions": [d["additions"] or 0 for d in data],
        "deletions": [d["deletions"] or 0 for d in data],
    })


@login_required
@require_GET
def api_pr_status(request):
    """Get pull request status distribution."""
    repo_ids = request.GET.getlist("repo_id")

    prs = PullRequest.objects.filter(repository__user=request.user)

    if repo_ids:
        prs = prs.filter(repository_id__in=repo_ids)

    open_count = prs.filter(state="open").count()
    merged_count = prs.filter(is_merged=True).count()
    closed_count = prs.filter(state="closed", is_merged=False).count()

    return JsonResponse({
        "labels": ["Open", "Merged", "Closed"],
        "data": [open_count, merged_count, closed_count],
        "colors": ["#fbc658", "#6bd098", "#ef8157"],
    })


@login_required
@require_GET
def api_contributions(request):
    """Get contribution breakdown by collaborator."""
    repo_ids = request.GET.getlist("repo_id")
    days = int(request.GET.get("days", 90))
    limit = int(request.GET.get("limit", 8))

    start_date = datetime.now() - timedelta(days=days)

    # Get commit counts
    commits = Commit.objects.filter(
        repository__user=request.user,
        authored_at__gte=start_date,
    )
    if repo_ids:
        commits = commits.filter(repository_id__in=repo_ids)

    commit_data = (
        commits.values("author_name")
        .annotate(commits=Count("id"))
        .order_by("-commits")[:limit]
    )

    # Get PR counts
    prs = PullRequest.objects.filter(
        repository__user=request.user,
        created_at__gte=start_date,
    )
    if repo_ids:
        prs = prs.filter(repository_id__in=repo_ids)

    pr_data = dict(
        prs.values("creator_username")
        .annotate(prs=Count("id"))
        .values_list("creator_username", "prs")
    )

    # Get review counts
    reviews = CodeReview.objects.filter(
        pull_request__repository__user=request.user,
        submitted_at__gte=start_date,
    )
    if repo_ids:
        reviews = reviews.filter(pull_request__repository_id__in=repo_ids)

    review_data = dict(
        reviews.values("reviewer_username")
        .annotate(reviews=Count("id"))
        .values_list("reviewer_username", "reviews")
    )

    # Combine data
    contributors = []
    for item in commit_data:
        name = item["author_name"]
        contributors.append({
            "name": name,
            "commits": item["commits"],
            "prs": pr_data.get(name, 0),
            "reviews": review_data.get(name, 0),
        })

    return JsonResponse({"contributors": contributors})


@login_required
@require_GET
def api_recent_commits(request):
    """Get recent commits for table display."""
    repo_ids = request.GET.getlist("repo_id")
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    commits = Commit.objects.filter(repository__user=request.user).select_related("repository")

    if repo_ids:
        commits = commits.filter(repository_id__in=repo_ids)

    commits = commits.order_by("-authored_at")[offset : offset + limit]

    data = [
        {
            "sha": c.sha[:7],
            "message": c.message[:100],
            "author_name": c.author_name,
            "authored_at": c.authored_at.isoformat(),
            "additions": c.additions,
            "deletions": c.deletions,
            "repository": c.repository.full_name,
        }
        for c in commits
    ]

    return JsonResponse({"commits": data})


@login_required
@require_GET
def api_recent_prs(request):
    """Get recent pull requests for table display."""
    repo_ids = request.GET.getlist("repo_id")
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    prs = PullRequest.objects.filter(repository__user=request.user).select_related("repository")

    if repo_ids:
        prs = prs.filter(repository_id__in=repo_ids)

    prs = prs.order_by("-created_at")[offset : offset + limit]

    data = [
        {
            "number": pr.number,
            "title": pr.title[:80],
            "state": "merged" if pr.is_merged else pr.state,
            "creator": pr.creator_username,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "repository": pr.repository.full_name,
        }
        for pr in prs
    ]

    return JsonResponse({"pull_requests": data})


@login_required
@require_GET
def api_recent_reviews(request):
    """Get recent code reviews for table display."""
    repo_ids = request.GET.getlist("repo_id")
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    reviews = CodeReview.objects.filter(
        pull_request__repository__user=request.user
    ).select_related("pull_request", "pull_request__repository")

    if repo_ids:
        reviews = reviews.filter(pull_request__repository_id__in=repo_ids)

    reviews = reviews.order_by("-submitted_at")[offset : offset + limit]

    data = [
        {
            "pr_number": r.pull_request.number,
            "pr_title": r.pull_request.title[:60],
            "reviewer": r.reviewer_username,
            "state": r.state,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "repository": r.pull_request.repository.full_name,
        }
        for r in reviews
    ]

    return JsonResponse({"reviews": data})


@login_required
@require_GET
def api_collaborators(request):
    """Get collaborators for filter dropdown."""
    repo_ids = request.GET.getlist("repo_id")

    if repo_ids:
        collaborators = Collaborator.objects.filter(
            repository_collaborators__repository_id__in=repo_ids,
            repository_collaborators__repository__user=request.user,
        ).distinct()
    else:
        collaborators = Collaborator.objects.filter(
            repository_collaborators__repository__user=request.user
        ).distinct()

    data = [
        {
            "id": c.id,
            "username": c.username,
            "avatar_url": c.avatar_url,
        }
        for c in collaborators[:50]
    ]

    return JsonResponse({"collaborators": data})


@login_required
@require_GET
def api_complexity_stats(request):
    """Get code complexity statistics."""
    repo_ids = request.GET.getlist("repo_id")

    from .models import FileAnalysis, FunctionAnalysis

    files = FileAnalysis.objects.filter(repository__user=request.user)
    if repo_ids:
        files = files.filter(repository_id__in=repo_ids)

    # Aggregate file stats
    file_stats = files.aggregate(
        total_files=Count("id"),
        total_nloc=Sum("nloc"),
        avg_ccn=Sum("ccn") / Count("id") if files.exists() else 0,
        total_functions=Sum("function_count"),
    )

    # Get high complexity functions
    functions = FunctionAnalysis.objects.filter(
        file_analysis__repository__user=request.user
    )
    if repo_ids:
        functions = functions.filter(file_analysis__repository_id__in=repo_ids)

    high_complexity = (
        functions.filter(ccn__gte=10)
        .select_related("file_analysis")
        .order_by("-ccn")[:10]
    )

    complex_functions = [
        {
            "name": f.function_name,
            "file": f.file_analysis.file_path,
            "ccn": f.ccn,
            "nloc": f.nloc,
        }
        for f in high_complexity
    ]

    # Language breakdown
    language_stats = (
        files.values("language")
        .annotate(count=Count("id"), nloc=Sum("nloc"))
        .order_by("-nloc")
    )

    return JsonResponse({
        "summary": file_stats,
        "high_complexity_functions": complex_functions,
        "languages": list(language_stats),
    })
