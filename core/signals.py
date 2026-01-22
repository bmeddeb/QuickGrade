"""
Signal handlers for OAuth social login and user actions.
"""

from allauth.socialaccount.signals import pre_social_login, social_account_added
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(pre_social_login)
def update_user_from_github(sender, request, sociallogin, **kwargs):
    """
    Update user profile fields from GitHub data on every login.
    This updates avatar, bio, and access token.
    """
    if sociallogin.account.provider != "github":
        return

    user = sociallogin.user
    if not user.pk:
        # New user - will be handled by social_account_added
        return

    extra_data = sociallogin.account.extra_data
    token = sociallogin.token.token if sociallogin.token else ""

    # Update user fields from GitHub profile
    user.github_id = str(extra_data.get("id", ""))
    user.avatar_url = extra_data.get("avatar_url", "")
    user.bio = extra_data.get("bio", "") or ""
    if token:
        user.access_token = token
    user.save(update_fields=["github_id", "avatar_url", "bio", "access_token"])


@receiver(social_account_added)
def populate_user_from_github(sender, request, sociallogin, **kwargs):
    """
    Populate user profile when a GitHub account is first connected.
    """
    if sociallogin.account.provider != "github":
        return

    user = sociallogin.user
    extra_data = sociallogin.account.extra_data
    token = sociallogin.token.token if sociallogin.token else ""

    user.github_id = str(extra_data.get("id", ""))
    user.avatar_url = extra_data.get("avatar_url", "")
    user.bio = extra_data.get("bio", "") or ""
    if token:
        user.access_token = token
    user.save(update_fields=["github_id", "avatar_url", "bio", "access_token"])


@receiver(user_logged_in)
def cleanup_orphaned_clones(sender, request, user, **kwargs):
    """Clean up any orphaned clone directories on user login."""
    from github_app.services.cleanup_service import CleanupService

    CleanupService.cleanup_user_clones(user)
