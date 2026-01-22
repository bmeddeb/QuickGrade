"""
Fetch orchestrator coordinating parallel clone and API fetching.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import transaction

from .analysis_service import AnalysisService, save_analysis_results
from .api_client import fetch_all_api_data
from .clone_service import CloneService, parse_repo_url

if TYPE_CHECKING:
    from core.models import User

logger = logging.getLogger(__name__)

# Progress stage percentages
PROGRESS_STAGES = {
    "initializing": (0, 5),
    "cloning": (5, 25),
    "extracting_commits": (25, 40),
    "analyzing_code": (40, 55),
    "fetching_api": (55, 80),
    "reconciling": (80, 95),
    "cleanup": (95, 100),
}


class FetchOrchestrator:
    """Coordinates parallel clone and API fetching."""

    def __init__(self, user: "User", repo_urls: list[str]):
        self.user = user
        self.repo_urls = repo_urls
        self.token = user.access_token
        self.progress_callback: callable | None = None
        self.results: list[dict] = []

    def _emit_progress(self, repo_url: str, stage: str, detail: str = "") -> None:
        """Emit progress update."""
        if self.progress_callback:
            stage_range = PROGRESS_STAGES.get(stage, (0, 100))
            self.progress_callback({
                "repo_url": repo_url,
                "stage": stage,
                "detail": detail,
                "progress_min": stage_range[0],
                "progress_max": stage_range[1],
            })

    async def _process_single_repo(self, repo_url: str) -> dict:
        """Process one repo - clone and API in parallel."""
        try:
            owner, repo_name = parse_repo_url(repo_url)
        except ValueError as e:
            return {"success": False, "repo_url": repo_url, "error": str(e)}

        self._emit_progress(repo_url, "initializing")

        # Create or get Repository record
        from github_app.models import Repository

        repo_obj, created = Repository.objects.get_or_create(
            user=self.user,
            full_name=f"{owner}/{repo_name}",
            defaults={
                "name": repo_name,
                "owner": owner,
                "url": repo_url,
                "fetch_status": "fetching",
            },
        )

        if not created:
            repo_obj.fetch_status = "fetching"
            repo_obj.fetch_error = ""
            repo_obj.save(update_fields=["fetch_status", "fetch_error", "updated_at"])

        try:
            # Run clone and API fetch in parallel
            clone_service = CloneService(repo_url, self.user, self.token)

            self._emit_progress(repo_url, "cloning")

            # Clone in thread, API fetch async
            clone_task = asyncio.to_thread(clone_service.clone_and_extract)

            self._emit_progress(repo_url, "fetching_api", "Starting API requests")

            api_task = fetch_all_api_data(
                self.token,
                owner,
                repo_name,
                progress_callback=lambda p: self._emit_progress(repo_url, "fetching_api", p.get("detail", "")),
            )

            # Wait for both
            clone_data, api_data = await asyncio.gather(
                clone_task,
                api_task,
                return_exceptions=True,
            )

            # Handle clone errors
            if isinstance(clone_data, Exception):
                logger.error(f"Clone failed for {repo_url}: {clone_data}")
                clone_data = {"success": False, "error": str(clone_data), "commits": [], "branches": []}
            elif not clone_data.get("success"):
                logger.error(f"Clone failed for {repo_url}: {clone_data.get('error')}")

            # Handle API errors
            if isinstance(api_data, Exception):
                logger.error(f"API fetch failed for {repo_url}: {api_data}")
                api_data = {"error": str(api_data)}

            # Run code analysis if clone succeeded
            analysis_data = None
            if clone_data.get("success") and clone_data.get("temp_path"):
                self._emit_progress(repo_url, "analyzing_code")
                try:
                    analyzer = AnalysisService(clone_data["temp_path"])
                    analysis_data = await asyncio.to_thread(analyzer.analyze_all)
                except Exception as e:
                    logger.exception(f"Analysis failed for {repo_url}: {e}")

            # Reconcile and save data
            self._emit_progress(repo_url, "reconciling")

            result = await asyncio.to_thread(
                self._save_all_data,
                repo_obj,
                clone_data,
                api_data,
                analysis_data,
            )

            # Cleanup clone directory
            self._emit_progress(repo_url, "cleanup")
            if clone_data.get("success"):
                clone_service.cleanup()

            # Update repository status
            repo_obj.fetch_status = "success"
            repo_obj.last_fetched_at = datetime.now(timezone.utc)
            repo_obj.save(update_fields=["fetch_status", "last_fetched_at", "updated_at"])

            return {
                "success": True,
                "repo_url": repo_url,
                "full_name": f"{owner}/{repo_name}",
                "repository_id": repo_obj.id,
                **result,
            }

        except Exception as e:
            logger.exception(f"Failed to process {repo_url}: {e}")
            repo_obj.fetch_status = "failed"
            repo_obj.fetch_error = str(e)
            repo_obj.save(update_fields=["fetch_status", "fetch_error", "updated_at"])
            return {
                "success": False,
                "repo_url": repo_url,
                "error": str(e),
            }

    @transaction.atomic
    def _save_all_data(
        self,
        repository: "Any",
        clone_data: dict,
        api_data: dict,
        analysis_data: dict | None,
    ) -> dict:
        """Save all fetched data to database."""
        from github_app.models import (
            Branch,
            CodeReview,
            Collaborator,
            Comment,
            Commit,
            Issue,
            PullRequest,
            RepositoryCollaborator,
        )

        stats = {
            "commits": 0,
            "branches": 0,
            "collaborators": 0,
            "pull_requests": 0,
            "reviews": 0,
            "issues": 0,
            "comments": 0,
            "files_analyzed": 0,
            "functions_analyzed": 0,
        }

        # Update repository info from API
        if "repository" in api_data:
            repo_info = api_data["repository"]
            repository.description = repo_info.get("description", "") or ""
            repository.default_branch = repo_info.get("default_branch", "main")
            repository.is_private = repo_info.get("private", False)
            repository.save(update_fields=["description", "default_branch", "is_private"])

        # Save collaborators (from API)
        collaborator_map = {}  # username -> Collaborator
        for collab_data in api_data.get("collaborators", []):
            collab, _ = Collaborator.objects.update_or_create(
                github_id=str(collab_data["id"]),
                defaults={
                    "username": collab_data["login"],
                    "avatar_url": collab_data.get("avatar_url", ""),
                    "profile_url": collab_data.get("html_url", ""),
                },
            )
            collaborator_map[collab_data["login"]] = collab

            # Create junction table entry
            RepositoryCollaborator.objects.update_or_create(
                repository=repository,
                collaborator=collab,
                defaults={
                    "permission": collab_data.get("role_name", "read"),
                },
            )
            stats["collaborators"] += 1

        # Save branches (prefer API data, fall back to clone data)
        existing_branches = {b.name for b in repository.branches.all()}
        api_branches = {b["name"] for b in api_data.get("branches", [])}

        for branch_data in api_data.get("branches", []):
            Branch.objects.update_or_create(
                repository=repository,
                name=branch_data["name"],
                defaults={
                    "sha": branch_data["commit"]["sha"],
                    "is_protected": branch_data.get("protected", False),
                    "is_default": branch_data["name"] == repository.default_branch,
                },
            )
            stats["branches"] += 1

        # Add branches from clone that aren't in API
        for branch_data in clone_data.get("branches", []):
            if branch_data["name"] not in api_branches:
                Branch.objects.update_or_create(
                    repository=repository,
                    name=branch_data["name"],
                    defaults={
                        "sha": branch_data["sha"],
                        "is_default": branch_data.get("is_default", False),
                    },
                )
                stats["branches"] += 1

        # Save commits (from clone)
        for commit_data in clone_data.get("commits", []):
            # Try to match commit author to collaborator
            author_collab = None
            for username, collab in collaborator_map.items():
                if (
                    commit_data["author_email"] == collab.email
                    or commit_data["author_name"].lower() == username.lower()
                ):
                    author_collab = collab
                    break

            Commit.objects.update_or_create(
                repository=repository,
                sha=commit_data["sha"],
                defaults={
                    "message": commit_data["message"],
                    "author_name": commit_data["author_name"],
                    "author_email": commit_data["author_email"],
                    "authored_at": commit_data["authored_at"],
                    "committer_name": commit_data["committer_name"],
                    "committer_email": commit_data["committer_email"],
                    "committed_at": commit_data["committed_at"],
                    "additions": commit_data["additions"],
                    "deletions": commit_data["deletions"],
                    "files_changed": commit_data["files_changed"],
                    "collaborator": author_collab,
                },
            )
            stats["commits"] += 1

        # Save pull requests (from API)
        pr_map = {}  # number -> PullRequest
        for pr_data in api_data.get("pull_requests", []):
            creator_collab = collaborator_map.get(pr_data["user"]["login"])

            pr, _ = PullRequest.objects.update_or_create(
                repository=repository,
                github_pr_id=pr_data["id"],
                defaults={
                    "number": pr_data["number"],
                    "title": pr_data["title"],
                    "body": pr_data.get("body", "") or "",
                    "state": "merged" if pr_data.get("merged_at") else pr_data["state"],
                    "is_merged": bool(pr_data.get("merged_at")),
                    "creator": creator_collab,
                    "creator_username": pr_data["user"]["login"],
                    "head_ref": pr_data["head"]["ref"],
                    "base_ref": pr_data["base"]["ref"],
                    "head_sha": pr_data["head"]["sha"],
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "changed_files": pr_data.get("changed_files", 0),
                    "commits_count": pr_data.get("commits", 0),
                    "comments_count": pr_data.get("comments", 0),
                    "review_comments_count": pr_data.get("review_comments", 0),
                    "created_at": pr_data["created_at"],
                    "updated_at": pr_data["updated_at"],
                    "merged_at": pr_data.get("merged_at"),
                    "closed_at": pr_data.get("closed_at"),
                },
            )
            pr_map[pr_data["number"]] = pr
            stats["pull_requests"] += 1

        # Save reviews (from API)
        for pr_number, reviews in api_data.get("pr_reviews", {}).items():
            pr = pr_map.get(pr_number)
            if not pr:
                continue

            for review_data in reviews:
                if not review_data.get("user"):
                    continue

                reviewer_collab = collaborator_map.get(review_data["user"]["login"])

                CodeReview.objects.update_or_create(
                    github_review_id=review_data["id"],
                    defaults={
                        "pull_request": pr,
                        "state": review_data["state"],
                        "body": review_data.get("body", "") or "",
                        "reviewer": reviewer_collab,
                        "reviewer_username": review_data["user"]["login"],
                        "submitted_at": review_data["submitted_at"],
                    },
                )
                stats["reviews"] += 1

        # Save issues (from API)
        issue_map = {}  # number -> Issue
        for issue_data in api_data.get("issues", []):
            creator_collab = collaborator_map.get(issue_data["user"]["login"])

            issue, _ = Issue.objects.update_or_create(
                github_issue_id=issue_data["id"],
                defaults={
                    "repository": repository,
                    "number": issue_data["number"],
                    "title": issue_data["title"],
                    "body": issue_data.get("body", "") or "",
                    "state": issue_data["state"],
                    "creator": creator_collab,
                    "creator_username": issue_data["user"]["login"],
                    "labels": [label["name"] for label in issue_data.get("labels", [])],
                    "comments_count": issue_data.get("comments", 0),
                    "created_at": issue_data["created_at"],
                    "updated_at": issue_data["updated_at"],
                    "closed_at": issue_data.get("closed_at"),
                },
            )
            issue_map[issue_data["number"]] = issue
            stats["issues"] += 1

        # Save issue comments (from API)
        for issue_number, comments in api_data.get("issue_comments", {}).items():
            issue = issue_map.get(issue_number)
            if not issue:
                continue

            for comment_data in comments:
                if not comment_data.get("user"):
                    continue

                author_collab = collaborator_map.get(comment_data["user"]["login"])

                Comment.objects.update_or_create(
                    github_comment_id=comment_data["id"],
                    defaults={
                        "issue": issue,
                        "body": comment_data["body"],
                        "author": author_collab,
                        "author_username": comment_data["user"]["login"],
                        "created_at": comment_data["created_at"],
                        "updated_at": comment_data["updated_at"],
                    },
                )
                stats["comments"] += 1

        # Save analysis results
        if analysis_data:
            files_saved, functions_saved = save_analysis_results(repository, analysis_data)
            stats["files_analyzed"] = files_saved
            stats["functions_analyzed"] = functions_saved

        return stats

    async def fetch_all(self) -> list[dict]:
        """Process all repos with controlled concurrency."""
        clone_workers = getattr(settings, "CLONE_WORKERS", 4)
        semaphore = asyncio.Semaphore(clone_workers)

        async def bounded_task(url: str) -> dict:
            async with semaphore:
                return await self._process_single_repo(url)

        self.results = await asyncio.gather(
            *[bounded_task(url) for url in self.repo_urls],
            return_exceptions=True,
        )

        # Convert exceptions to error dicts
        processed_results = []
        for i, result in enumerate(self.results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "repo_url": self.repo_urls[i],
                    "error": str(result),
                })
            else:
                processed_results.append(result)

        return processed_results
