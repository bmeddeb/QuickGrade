"""
Taiga app views - Dashboard, Fetch.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """Taiga analytics dashboard."""
    return render(request, "taiga/dashboard.html")


@login_required
def fetch(request):
    """Fetch Taiga data page."""
    return render(request, "taiga/fetch.html")
