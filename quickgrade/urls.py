"""
URL configuration for quickgrade project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("github/", include("github_app.urls")),
    path("taiga/", include("taiga_app.urls")),
    path("", include("core.urls")),
]
