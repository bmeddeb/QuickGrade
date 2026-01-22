"""
Core models - User and UserPreferences.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with GitHub profile fields."""

    github_id = models.CharField(max_length=50, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    access_token = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.username or self.email


class UserPreferences(models.Model):
    """User preferences for dashboard customization."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")

    # Color palettes (JSON array of {id, name, colors[]})
    palettes = models.JSONField(default=list)
    active_palette_id = models.CharField(max_length=36, blank=True)

    # Excluded usernames (for filtering bots, etc.)
    excluded_usernames = models.JSONField(default=list)

    # Activity gap threshold (days)
    gap_threshold = models.IntegerField(default=4)

    # Taiga task status colors
    task_colors = models.JSONField(default=dict)

    class Meta:
        verbose_name_plural = "User preferences"

    def __str__(self):
        return f"Preferences for {self.user}"

    def save(self, *args, **kwargs):
        # Set defaults on first save
        if not self.pk:
            if not self.palettes:
                self.palettes = [
                    {"id": "default", "name": "Default", "colors": ["#51cbce", "#fbc658", "#ef8157", "#6bd098", "#51bcda"]},
                    {"id": "paper", "name": "Paper", "colors": ["#f96332", "#66615b", "#51cbce", "#6bd098", "#fbc658"]},
                ]
            if not self.excluded_usernames:
                self.excluded_usernames = ["root", "Local Administrator", "Administrator", "dependabot[bot]"]
        super().save(*args, **kwargs)
