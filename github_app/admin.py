"""
GitHub app admin configuration.
"""

from django.contrib import admin

from .models import (
    Branch,
    CloneTracker,
    CodeReview,
    Collaborator,
    Comment,
    Commit,
    FileAnalysis,
    FunctionAnalysis,
    Issue,
    Notification,
    PullRequest,
    Repository,
    RepositoryCollaborator,
)


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "fetch_status", "last_fetched_at", "updated_at"]
    list_filter = ["fetch_status", "is_private"]
    search_fields = ["full_name", "owner", "name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Collaborator)
class CollaboratorAdmin(admin.ModelAdmin):
    list_display = ["username", "name", "email", "github_id"]
    search_fields = ["username", "name", "email"]


@admin.register(RepositoryCollaborator)
class RepositoryCollaboratorAdmin(admin.ModelAdmin):
    list_display = ["collaborator", "repository", "permission", "color"]
    list_filter = ["permission"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "repository", "is_default", "is_protected", "is_merged"]
    list_filter = ["is_default", "is_protected", "is_merged"]


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ["sha_short", "author_name", "repository", "authored_at", "additions", "deletions"]
    list_filter = ["repository"]
    search_fields = ["sha", "message", "author_name", "author_email"]

    def sha_short(self, obj):
        return obj.sha[:7]

    sha_short.short_description = "SHA"


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ["number", "title", "repository", "state", "creator_username", "created_at"]
    list_filter = ["state", "is_merged", "repository"]
    search_fields = ["title", "creator_username"]


@admin.register(CodeReview)
class CodeReviewAdmin(admin.ModelAdmin):
    list_display = ["reviewer_username", "pull_request", "state", "submitted_at"]
    list_filter = ["state"]


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["number", "title", "repository", "state", "creator_username", "created_at"]
    list_filter = ["state", "repository"]
    search_fields = ["title", "creator_username"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author_username", "get_parent", "created_at"]

    def get_parent(self, obj):
        return obj.pull_request or obj.issue

    get_parent.short_description = "Parent"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["notification_type", "collaborator", "repository", "user", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read"]


@admin.register(CloneTracker)
class CloneTrackerAdmin(admin.ModelAdmin):
    list_display = ["repo_url", "status", "user", "created_at", "updated_at"]
    list_filter = ["status"]


@admin.register(FileAnalysis)
class FileAnalysisAdmin(admin.ModelAdmin):
    list_display = ["file_path", "repository", "language", "nloc", "ccn", "function_count"]
    list_filter = ["language", "repository"]
    search_fields = ["file_path"]


@admin.register(FunctionAnalysis)
class FunctionAnalysisAdmin(admin.ModelAdmin):
    list_display = ["function_name", "file_analysis", "nloc", "ccn", "parameter_count"]
    search_fields = ["function_name"]
