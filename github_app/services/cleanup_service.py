"""
Cleanup service for orphaned clone directories.
"""

import logging
import os
import shutil
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from core.models import User

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up orphaned clone directories."""

    @staticmethod
    def cleanup_user_clones(user: "User") -> int:
        """
        Clean up orphaned clone directories for a user.
        Called on user login.
        Returns number of directories cleaned.
        """
        from github_app.models import CloneTracker

        cleaned = 0

        # Find orphaned trackers (stuck in intermediate states)
        orphans = CloneTracker.objects.filter(
            user=user,
            status__in=["cloning", "extracting", "analyzing"],
        )

        for tracker in orphans:
            if tracker.temp_path and os.path.exists(tracker.temp_path):
                try:
                    shutil.rmtree(tracker.temp_path, ignore_errors=True)
                    logger.info(f"Cleaned up orphaned directory: {tracker.temp_path}")
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup {tracker.temp_path}: {e}")

            tracker.status = "cleaned"
            tracker.temp_path = ""
            tracker.save(update_fields=["status", "temp_path", "updated_at"])

        # Also cleanup pending_cleanup trackers older than 1 hour
        cutoff = timezone.now() - timedelta(hours=1)
        stale = CloneTracker.objects.filter(
            user=user,
            status="pending_cleanup",
            updated_at__lt=cutoff,
        )

        for tracker in stale:
            if tracker.temp_path and os.path.exists(tracker.temp_path):
                try:
                    shutil.rmtree(tracker.temp_path, ignore_errors=True)
                    logger.info(f"Cleaned up stale directory: {tracker.temp_path}")
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup {tracker.temp_path}: {e}")

            tracker.status = "cleaned"
            tracker.temp_path = ""
            tracker.save(update_fields=["status", "temp_path", "updated_at"])

        if cleaned:
            logger.info(f"Cleaned up {cleaned} orphaned clone directories for user {user.username}")

        return cleaned

    @staticmethod
    def cleanup_all_stale() -> int:
        """
        Clean up all stale clone directories.
        Called by periodic Celery task.
        Returns number of directories cleaned.
        """
        from github_app.models import CloneTracker

        cleaned = 0
        cutoff = timezone.now() - timedelta(hours=1)

        # Find all stale trackers
        stale = CloneTracker.objects.filter(
            status__in=["cloning", "extracting", "analyzing", "pending_cleanup"],
            updated_at__lt=cutoff,
        )

        for tracker in stale:
            if tracker.temp_path and os.path.exists(tracker.temp_path):
                try:
                    shutil.rmtree(tracker.temp_path, ignore_errors=True)
                    logger.info(f"Cleaned up stale directory: {tracker.temp_path}")
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup {tracker.temp_path}: {e}")

            tracker.status = "cleaned"
            tracker.temp_path = ""
            tracker.save(update_fields=["status", "temp_path", "updated_at"])

        if cleaned:
            logger.info(f"Cleaned up {cleaned} stale clone directories")

        return cleaned

    @staticmethod
    def cleanup_directory(path: str) -> bool:
        """
        Clean up a specific directory.
        Returns True if successful.
        """
        if not path or not os.path.exists(path):
            return True

        try:
            shutil.rmtree(path, ignore_errors=True)
            logger.info(f"Cleaned up directory: {path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
            return False
