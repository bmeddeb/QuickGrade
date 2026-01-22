"""
Core views - Home, Profile, Preferences, Upload.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home(request):
    """Home page - redirect to login if not authenticated, otherwise dashboard."""
    if not request.user.is_authenticated:
        return redirect("account_login")
    return render(request, "dashboard.html")


@login_required
def profile(request):
    """User profile page."""
    return render(request, "profile.html")


@login_required
def preferences(request):
    """User preferences page."""
    return render(request, "preferences.html")


@login_required
def upload(request):
    """File upload page for CSV/Excel import."""
    return render(request, "upload.html")
