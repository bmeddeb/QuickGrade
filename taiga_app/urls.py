"""
Taiga app URL configuration.
"""

from django.urls import path

from . import views

app_name = "taiga"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("fetch/", views.fetch, name="fetch"),
]
