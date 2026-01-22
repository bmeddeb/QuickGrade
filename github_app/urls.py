"""
GitHub app URL configuration.
"""

from django.urls import path

from . import api, views

app_name = "github"

urlpatterns = [
    # Dashboard views
    path("", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics_dashboard, name="analytics"),
    path("fetch/", views.fetch, name="fetch"),
    path("fetch/progress/<str:task_id>/", views.fetch_progress, name="fetch_progress"),
    path("fetch/status/<str:task_id>/", views.task_status, name="task_status"),
    path("repo/<int:repo_id>/", views.repository_detail, name="repository_detail"),
    path("repo/<int:repo_id>/commits/", views.repository_commits, name="repository_commits"),
    path("repo/<int:repo_id>/prs/", views.repository_prs, name="repository_prs"),
    path("repo/<int:repo_id>/issues/", views.repository_issues, name="repository_issues"),
    path("repo/<int:repo_id>/analysis/", views.repository_analysis, name="repository_analysis"),
    path("repo/<int:repo_id>/delete/", views.repository_delete, name="repository_delete"),
    # API endpoints
    path("api/repositories/", api.api_repositories, name="api_repositories"),
    path("api/repositories/<int:repo_id>/stats/", api.api_repository_stats, name="api_repository_stats"),
    path("api/commits/over-time/", api.api_commits_over_time, name="api_commits_over_time"),
    path("api/commits/by-author/", api.api_commits_by_author, name="api_commits_by_author"),
    path("api/commits/recent/", api.api_recent_commits, name="api_recent_commits"),
    path("api/prs/status/", api.api_pr_status, name="api_pr_status"),
    path("api/prs/recent/", api.api_recent_prs, name="api_recent_prs"),
    path("api/reviews/recent/", api.api_recent_reviews, name="api_recent_reviews"),
    path("api/contributions/", api.api_contributions, name="api_contributions"),
    path("api/collaborators/", api.api_collaborators, name="api_collaborators"),
    path("api/complexity/", api.api_complexity_stats, name="api_complexity_stats"),
]
