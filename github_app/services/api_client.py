"""
Async GitHub API client with rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class RateLimitExceeded(Exception):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_at: datetime):
        self.reset_at = reset_at
        super().__init__(f"Rate limit exceeded. Resets at {reset_at}")


class GitHubAPIClient:
    """Async GitHub API client with rate limiting."""

    def __init__(self, token: str):
        self.token = token
        self.semaphore = asyncio.Semaphore(getattr(settings, "API_CONCURRENCY", 20))
        self.rate_limit_remaining = 5000
        self.rate_limit_reset: datetime | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers."""
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        if remaining:
            self.rate_limit_remaining = int(remaining)
        if reset:
            self.rate_limit_reset = datetime.fromtimestamp(int(reset), tz=timezone.utc)

    async def _wait_for_reset(self) -> None:
        """Wait for rate limit reset if needed."""
        if self.rate_limit_reset:
            now = datetime.now(timezone.utc)
            wait_seconds = (self.rate_limit_reset - now).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"Rate limit low, waiting {wait_seconds:.0f}s for reset")
                await asyncio.sleep(min(wait_seconds + 1, 60))  # Cap at 60s

    async def fetch(self, endpoint: str, params: dict | None = None) -> dict | list:
        """Fetch from GitHub API with rate limit handling."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        async with self.semaphore:
            threshold = getattr(settings, "RATE_LIMIT_THRESHOLD", 100)
            if self.rate_limit_remaining < threshold:
                await self._wait_for_reset()

            response = await self._client.get(endpoint, params=params)
            self._update_rate_limit(response.headers)

            if response.status_code == 403 and self.rate_limit_remaining == 0:
                raise RateLimitExceeded(self.rate_limit_reset or datetime.now(timezone.utc))

            response.raise_for_status()
            return response.json()

    async def fetch_paginated(
        self,
        endpoint: str,
        params: dict | None = None,
        max_pages: int = 100,
    ) -> list[Any]:
        """Fetch all pages from a paginated endpoint."""
        params = params or {}
        params.setdefault("per_page", 100)
        params.setdefault("page", 1)

        all_results = []
        page = 1

        while page <= max_pages:
            params["page"] = page
            results = await self.fetch(endpoint, params)

            if not results:
                break

            if isinstance(results, list):
                all_results.extend(results)
                if len(results) < params["per_page"]:
                    break
            else:
                all_results.append(results)
                break

            page += 1

        return all_results

    # Repository endpoints
    async def fetch_repository(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata."""
        return await self.fetch(f"/repos/{owner}/{repo}")

    # Collaborator endpoints
    async def fetch_collaborators(self, owner: str, repo: str) -> list[dict]:
        """Fetch repository collaborators."""
        try:
            return await self.fetch_paginated(f"/repos/{owner}/{repo}/collaborators")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # Not authorized to view collaborators, try contributors
                logger.warning(f"Cannot access collaborators for {owner}/{repo}, trying contributors")
                return await self.fetch_contributors(owner, repo)
            raise

    async def fetch_contributors(self, owner: str, repo: str) -> list[dict]:
        """Fetch repository contributors (public endpoint)."""
        return await self.fetch_paginated(f"/repos/{owner}/{repo}/contributors")

    # Branch endpoints
    async def fetch_branches(self, owner: str, repo: str) -> list[dict]:
        """Fetch repository branches."""
        return await self.fetch_paginated(f"/repos/{owner}/{repo}/branches")

    # Pull request endpoints
    async def fetch_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
    ) -> list[dict]:
        """Fetch pull requests."""
        return await self.fetch_paginated(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "sort": "created", "direction": "desc"},
        )

    async def fetch_pr_reviews(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict]:
        """Fetch reviews for a pull request."""
        return await self.fetch_paginated(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")

    async def fetch_pr_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict]:
        """Fetch comments on a pull request."""
        return await self.fetch_paginated(f"/repos/{owner}/{repo}/pulls/{pr_number}/comments")

    # Issue endpoints
    async def fetch_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
    ) -> list[dict]:
        """Fetch issues (excluding PRs)."""
        all_items = await self.fetch_paginated(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "sort": "created", "direction": "desc"},
        )
        # Filter out pull requests (they appear in issues endpoint)
        return [item for item in all_items if "pull_request" not in item]

    async def fetch_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> list[dict]:
        """Fetch comments on an issue."""
        return await self.fetch_paginated(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")

    # User endpoints
    async def fetch_user(self, username: str) -> dict:
        """Fetch user profile."""
        return await self.fetch(f"/users/{username}")

    # Rate limit endpoint
    async def get_rate_limit(self) -> dict:
        """Get current rate limit status."""
        return await self.fetch("/rate_limit")


async def fetch_all_api_data(
    token: str,
    owner: str,
    repo: str,
    progress_callback: Any | None = None,
) -> dict:
    """
    Fetch all API data for a repository.
    Returns dict with all fetched data.
    """
    async with GitHubAPIClient(token) as client:
        # Fetch in parallel where possible
        repo_info, collaborators, branches = await asyncio.gather(
            client.fetch_repository(owner, repo),
            client.fetch_collaborators(owner, repo),
            client.fetch_branches(owner, repo),
            return_exceptions=True,
        )

        # Handle errors
        if isinstance(repo_info, Exception):
            raise repo_info

        # Convert exceptions to empty lists
        if isinstance(collaborators, Exception):
            logger.warning(f"Failed to fetch collaborators: {collaborators}")
            collaborators = []
        if isinstance(branches, Exception):
            logger.warning(f"Failed to fetch branches: {branches}")
            branches = []

        if progress_callback:
            progress_callback({"stage": "fetching_api", "detail": "PRs and issues"})

        # Fetch PRs and issues
        pull_requests, issues = await asyncio.gather(
            client.fetch_pull_requests(owner, repo),
            client.fetch_issues(owner, repo),
            return_exceptions=True,
        )

        if isinstance(pull_requests, Exception):
            logger.warning(f"Failed to fetch PRs: {pull_requests}")
            pull_requests = []
        if isinstance(issues, Exception):
            logger.warning(f"Failed to fetch issues: {issues}")
            issues = []

        if progress_callback:
            progress_callback({"stage": "fetching_api", "detail": "reviews and comments"})

        # Fetch reviews for all PRs (parallel)
        pr_reviews = {}
        if pull_requests:
            review_tasks = [
                client.fetch_pr_reviews(owner, repo, pr["number"])
                for pr in pull_requests
            ]
            review_results = await asyncio.gather(*review_tasks, return_exceptions=True)
            for pr, reviews in zip(pull_requests, review_results):
                if isinstance(reviews, Exception):
                    logger.warning(f"Failed to fetch reviews for PR#{pr['number']}: {reviews}")
                    pr_reviews[pr["number"]] = []
                else:
                    pr_reviews[pr["number"]] = reviews

        # Fetch comments for issues (parallel)
        issue_comments = {}
        if issues:
            comment_tasks = [
                client.fetch_issue_comments(owner, repo, issue["number"])
                for issue in issues
            ]
            comment_results = await asyncio.gather(*comment_tasks, return_exceptions=True)
            for issue, comments in zip(issues, comment_results):
                if isinstance(comments, Exception):
                    logger.warning(f"Failed to fetch comments for Issue#{issue['number']}: {comments}")
                    issue_comments[issue["number"]] = []
                else:
                    issue_comments[issue["number"]] = comments

        return {
            "repository": repo_info,
            "collaborators": collaborators,
            "branches": branches,
            "pull_requests": pull_requests,
            "pr_reviews": pr_reviews,
            "issues": issues,
            "issue_comments": issue_comments,
            "rate_limit_remaining": client.rate_limit_remaining,
        }
