"""
Clone service for git repository cloning and commit extraction.
"""

import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django.conf import settings
from git import Repo
from git.exc import GitCommandError

if TYPE_CHECKING:
    from core.models import User
    from github_app.models import CloneTracker, Repository

logger = logging.getLogger(__name__)


def parse_repo_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name."""
    # Handle various GitHub URL formats
    # https://github.com/owner/repo
    # https://github.com/owner/repo.git
    # git@github.com:owner/repo.git
    url = url.strip().rstrip("/")

    if url.startswith("git@"):
        # SSH format: git@github.com:owner/repo.git
        match = re.match(r"git@github\.com:(.+)/(.+?)(?:\.git)?$", url)
        if match:
            return match.group(1), match.group(2)
    else:
        # HTTPS format
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    raise ValueError(f"Could not parse GitHub URL: {url}")


class CloneService:
    """Handles git clone and local data extraction."""

    def __init__(self, repo_url: str, user: "User", token: str | None = None):
        self.repo_url = repo_url
        self.user = user
        self.token = token or user.access_token
        self.tracker: "CloneTracker | None" = None
        self.temp_dir: str | None = None
        self.owner: str = ""
        self.repo_name: str = ""

        try:
            self.owner, self.repo_name = parse_repo_url(repo_url)
        except ValueError as e:
            logger.error(f"Failed to parse repo URL: {e}")
            raise

    def _get_clone_url(self) -> str:
        """Get authenticated clone URL."""
        if self.token:
            return f"https://x-access-token:{self.token}@github.com/{self.owner}/{self.repo_name}.git"
        return f"https://github.com/{self.owner}/{self.repo_name}.git"

    def _create_tracker(self) -> "CloneTracker":
        """Create CloneTracker record."""
        from github_app.models import CloneTracker

        self.tracker = CloneTracker.objects.create(
            user=self.user,
            repo_url=self.repo_url,
            status="cloning",
        )
        return self.tracker

    def _update_tracker(self, status: str, error_message: str = "") -> None:
        """Update tracker status."""
        if self.tracker:
            self.tracker.status = status
            self.tracker.error_message = error_message
            if self.temp_dir:
                self.tracker.temp_path = self.temp_dir
            self.tracker.save(update_fields=["status", "error_message", "temp_path", "updated_at"])

    def clone(self) -> str:
        """Clone repository to temporary directory."""
        # Create temp directory
        clone_base = getattr(settings, "CLONE_TEMP_DIR", tempfile.gettempdir())
        os.makedirs(clone_base, exist_ok=True)

        self.temp_dir = tempfile.mkdtemp(
            prefix=f"qg_{self.owner}_{self.repo_name}_",
            dir=clone_base,
        )

        try:
            clone_url = self._get_clone_url()
            logger.info(f"Cloning {self.owner}/{self.repo_name} to {self.temp_dir}")

            # Clone with depth for faster initial clone, then fetch full history
            Repo.clone_from(
                clone_url,
                self.temp_dir,
                multi_options=["--no-single-branch"],  # Get all branches
            )

            logger.info(f"Clone completed: {self.temp_dir}")
            return self.temp_dir

        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            self._update_tracker("failed", str(e))
            raise

    def extract_commits(self, repo_path: str | None = None) -> list[dict]:
        """Extract all commits from cloned repository."""
        path = repo_path or self.temp_dir
        if not path:
            raise ValueError("No repository path available")

        repo = Repo(path)
        commits = []

        for branch in repo.references:
            try:
                for commit in repo.iter_commits(branch):
                    # Get commit stats
                    stats = commit.stats.total
                    commits.append({
                        "sha": commit.hexsha,
                        "message": commit.message.strip(),
                        "author_name": commit.author.name,
                        "author_email": commit.author.email or "",
                        "authored_at": datetime.fromtimestamp(commit.authored_date, tz=timezone.utc),
                        "committer_name": commit.committer.name,
                        "committer_email": commit.committer.email or "",
                        "committed_at": datetime.fromtimestamp(commit.committed_date, tz=timezone.utc),
                        "additions": stats.get("insertions", 0),
                        "deletions": stats.get("deletions", 0),
                        "files_changed": stats.get("files", 0),
                    })
            except Exception as e:
                logger.warning(f"Error processing branch {branch}: {e}")
                continue

        # Deduplicate by SHA (commits can appear on multiple branches)
        seen_shas = set()
        unique_commits = []
        for commit in commits:
            if commit["sha"] not in seen_shas:
                seen_shas.add(commit["sha"])
                unique_commits.append(commit)

        logger.info(f"Extracted {len(unique_commits)} unique commits")
        return unique_commits

    def extract_branches(self, repo_path: str | None = None) -> list[dict]:
        """Extract branch information from cloned repository."""
        path = repo_path or self.temp_dir
        if not path:
            raise ValueError("No repository path available")

        repo = Repo(path)
        branches = []

        # Get default branch
        try:
            default_branch = repo.active_branch.name
        except TypeError:
            default_branch = "main"

        for ref in repo.references:
            if hasattr(ref, "remote_head"):
                # This is a remote tracking branch
                branch_name = ref.remote_head
                if branch_name == "HEAD":
                    continue
                branches.append({
                    "name": branch_name,
                    "sha": ref.commit.hexsha,
                    "is_default": branch_name == default_branch,
                    "is_protected": False,  # Can't determine from local clone
                    "is_merged": False,  # Will be updated from API
                })

        logger.info(f"Extracted {len(branches)} branches")
        return branches

    def clone_and_extract(self) -> dict:
        """
        Full clone and extraction pipeline.
        Designed to run in thread via asyncio.to_thread().
        """
        self._create_tracker()

        try:
            # Step 1: Clone
            self._update_tracker("cloning")
            repo_path = self.clone()

            # Step 2: Extract commits
            self._update_tracker("extracting")
            commits = self.extract_commits(repo_path)
            branches = self.extract_branches(repo_path)

            # Step 3: Mark for cleanup (analysis happens separately)
            self._update_tracker("pending_cleanup")

            return {
                "success": True,
                "owner": self.owner,
                "repo_name": self.repo_name,
                "full_name": f"{self.owner}/{self.repo_name}",
                "temp_path": self.temp_dir,
                "commits": commits,
                "branches": branches,
                "tracker_id": self.tracker.id if self.tracker else None,
            }

        except Exception as e:
            logger.exception(f"Clone and extract failed for {self.repo_url}")
            self._update_tracker("failed", str(e))
            self.cleanup()
            return {
                "success": False,
                "owner": self.owner,
                "repo_name": self.repo_name,
                "full_name": f"{self.owner}/{self.repo_name}",
                "error": str(e),
            }

    def cleanup(self) -> None:
        """Remove temporary clone directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {self.temp_dir}: {e}")

        if self.tracker:
            self._update_tracker("cleaned")
            self.tracker.temp_path = ""
            self.tracker.save(update_fields=["temp_path", "updated_at"])
