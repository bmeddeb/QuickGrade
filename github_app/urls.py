"""
GitHub app URL configuration.
"""

from django.urls import path

from . import views

app_name = "github"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("fetch/", views.fetch, name="fetch"),
    path("fetch/progress/<str:task_id>/", views.fetch_progress, name="fetch_progress"),
    path("fetch/status/<str:task_id>/", views.task_status, name="task_status"),
    path("repo/<int:repo_id>/", views.repository_detail, name="repository_detail"),
    path("repo/<int:repo_id>/commits/", views.repository_commits, name="repository_commits"),
    path("repo/<int:repo_id>/prs/", views.repository_prs, name="repository_prs"),
    path("repo/<int:repo_id>/issues/", views.repository_issues, name="repository_issues"),
    path("repo/<int:repo_id>/analysis/", views.repository_analysis, name="repository_analysis"),
]
