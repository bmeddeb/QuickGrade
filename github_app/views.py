"""
GitHub app views - Dashboard, Fetch.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """GitHub analytics dashboard."""
    return render(request, "github/dashboard.html")


@login_required
def fetch(request):
    """Fetch GitHub data page."""
    return render(request, "github/fetch.html")
