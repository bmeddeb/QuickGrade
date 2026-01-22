"""
Celery tasks for GitHub data fetching.
"""

import asyncio
import logging

from celery import shared_task

from core.models import User

from .services.cleanup_service import CleanupService
from .services.fetch_service import FetchOrchestrator

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_repositories(self, user_id: int, repo_urls: list[str]):
    """
    Background task to fetch GitHub data for multiple repositories.

    Args:
        user_id: The user who initiated the fetch
        repo_urls: List of GitHub repository URLs to process

    Returns:
        Dict with status and results summary
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"status": "error", "error": "User not found"}

    if not user.access_token:
        logger.error(f"User {user.username} has no access token")
        return {"status": "error", "error": "No GitHub access token"}

    orchestrator = FetchOrchestrator(user, repo_urls)

    # Set up progress callback for Celery state updates
    def progress_callback(progress_data):
        self.update_state(
            state="PROGRESS",
            meta={
                "current_repo": progress_data.get("repo_url"),
                "stage": progress_data.get("stage"),
                "detail": progress_data.get("detail"),
                "progress_min": progress_data.get("progress_min", 0),
                "progress_max": progress_data.get("progress_max", 100),
            },
        )

    orchestrator.progress_callback = progress_callback

    # Run async orchestrator in sync Celery task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(orchestrator.fetch_all())
    finally:
        loop.close()

    # Summarize results
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful

    total_commits = sum(r.get("commits", 0) for r in results if r.get("success"))
    total_prs = sum(r.get("pull_requests", 0) for r in results if r.get("success"))
    total_issues = sum(r.get("issues", 0) for r in results if r.get("success"))

    return {
        "status": "complete",
        "repos_processed": len(results),
        "successful": successful,
        "failed": failed,
        "total_commits": total_commits,
        "total_pull_requests": total_prs,
        "total_issues": total_issues,
        "results": results,
    }


@shared_task
def cleanup_stale_clones():
    """
    Periodic task to clean up stale clone directories.
    Should be scheduled to run hourly.
    """
    cleaned = CleanupService.cleanup_all_stale()
    return {"cleaned": cleaned}


@shared_task
def fetch_single_repository(user_id: int, repo_url: str):
    """
    Fetch data for a single repository.
    Convenience wrapper around process_repositories for single repo.
    """
    result = process_repositories(user_id, [repo_url])
    if result.get("results"):
        return result["results"][0]
    return result
