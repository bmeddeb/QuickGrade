"""
GitHub app models for repositories, commits, PRs, issues, and code analysis.
"""

from django.conf import settings
from django.db import models


class Repository(models.Model):
    """Central repository model linked to user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="repositories",
    )
    name = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)
    full_name = models.CharField(max_length=512)  # owner/name
    url = models.URLField()
    description = models.TextField(blank=True)
    default_branch = models.CharField(max_length=255, default="main")
    is_private = models.BooleanField(default=False)

    # Fetch metadata
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    fetch_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("fetching", "Fetching"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    fetch_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Repositories"
        unique_together = ["user", "full_name"]
        ordering = ["-updated_at"]

    def __str__(self):
        return self.full_name


class Collaborator(models.Model):
    """GitHub user who contributes to repositories."""

    github_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=255)
    avatar_url = models.URLField(blank=True)
    profile_url = models.URLField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class RepositoryCollaborator(models.Model):
    """Junction table for Repository-Collaborator with additional fields."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="repository_collaborators",
    )
    collaborator = models.ForeignKey(
        Collaborator,
        on_delete=models.CASCADE,
        related_name="repository_collaborators",
    )
    color = models.CharField(max_length=7, blank=True)  # Hex color for charts
    permission = models.CharField(
        max_length=20,
        choices=[
            ("admin", "Admin"),
            ("maintain", "Maintain"),
            ("write", "Write"),
            ("triage", "Triage"),
            ("read", "Read"),
        ],
        default="read",
    )

    class Meta:
        unique_together = ["repository", "collaborator"]

    def __str__(self):
        return f"{self.collaborator.username} on {self.repository.full_name}"


class Branch(models.Model):
    """Repository branch information."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="branches",
    )
    name = models.CharField(max_length=255)
    sha = models.CharField(max_length=40)  # Latest commit SHA
    is_default = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)
    is_merged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Branches"
        unique_together = ["repository", "name"]

    def __str__(self):
        return f"{self.repository.full_name}:{self.name}"


class Commit(models.Model):
    """Git commit data extracted from repository."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="commits",
    )
    sha = models.CharField(max_length=40)
    message = models.TextField()
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField(blank=True)
    authored_at = models.DateTimeField()
    committer_name = models.CharField(max_length=255)
    committer_email = models.EmailField(blank=True)
    committed_at = models.DateTimeField()

    # Stats
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    files_changed = models.IntegerField(default=0)

    # Link to collaborator (matched by email/name after fetch)
    collaborator = models.ForeignKey(
        Collaborator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commits",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sha", "repository"], name="unique_commit_per_repo"),
        ]
        ordering = ["-authored_at"]

    def __str__(self):
        return f"{self.sha[:7]} - {self.message[:50]}"


class PullRequest(models.Model):
    """Pull request data from GitHub API."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="pull_requests",
    )
    github_pr_id = models.BigIntegerField()
    number = models.IntegerField()
    title = models.CharField(max_length=512)
    body = models.TextField(blank=True)
    state = models.CharField(
        max_length=20,
        choices=[
            ("open", "Open"),
            ("closed", "Closed"),
            ("merged", "Merged"),
        ],
    )
    is_merged = models.BooleanField(default=False)

    # Author info
    creator = models.ForeignKey(
        Collaborator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_prs",
    )
    creator_username = models.CharField(max_length=255)

    # Branch info
    head_ref = models.CharField(max_length=255)
    base_ref = models.CharField(max_length=255)
    head_sha = models.CharField(max_length=40)

    # Stats
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    changed_files = models.IntegerField(default=0)
    commits_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    review_comments_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    merged_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["github_pr_id", "repository"], name="unique_pr_per_repo"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.number} - {self.title}"


class CodeReview(models.Model):
    """PR review data from GitHub API."""

    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    github_review_id = models.BigIntegerField(unique=True)
    state = models.CharField(
        max_length=30,
        choices=[
            ("APPROVED", "Approved"),
            ("CHANGES_REQUESTED", "Changes Requested"),
            ("COMMENTED", "Commented"),
            ("DISMISSED", "Dismissed"),
            ("PENDING", "Pending"),
        ],
    )
    body = models.TextField(blank=True)

    # Reviewer info
    reviewer = models.ForeignKey(
        Collaborator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    reviewer_username = models.CharField(max_length=255)

    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Review by {self.reviewer_username} on PR#{self.pull_request.number}"


class Issue(models.Model):
    """Issue data from GitHub API."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="issues",
    )
    github_issue_id = models.BigIntegerField(unique=True)
    number = models.IntegerField()
    title = models.CharField(max_length=512)
    body = models.TextField(blank=True)
    state = models.CharField(
        max_length=20,
        choices=[
            ("open", "Open"),
            ("closed", "Closed"),
        ],
    )

    # Author info
    creator = models.ForeignKey(
        Collaborator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_issues",
    )
    creator_username = models.CharField(max_length=255)

    # Labels (stored as JSON array)
    labels = models.JSONField(default=list)
    comments_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.number} - {self.title}"


class Comment(models.Model):
    """Comments on PRs or Issues."""

    github_comment_id = models.BigIntegerField(unique=True)
    body = models.TextField()

    # Polymorphic: either PR or Issue
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )

    # Author info
    author = models.ForeignKey(
        Collaborator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    author_username = models.CharField(max_length=255)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        parent = self.pull_request or self.issue
        return f"Comment by {self.author_username} on {parent}"


class Notification(models.Model):
    """Activity gap notifications for users."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="github_notifications",
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    collaborator = models.ForeignKey(
        Collaborator,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=[
            ("activity_gap", "Activity Gap"),
            ("no_commits", "No Commits"),
            ("no_reviews", "No Reviews"),
        ],
    )
    message = models.TextField()
    gap_days = models.IntegerField(default=0)
    gap_start = models.DateTimeField(null=True, blank=True)
    gap_end = models.DateTimeField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.collaborator.username}"


class CloneTracker(models.Model):
    """Track temporary clone directories for cleanup."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clone_trackers",
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="clone_trackers",
    )
    repo_url = models.URLField()
    temp_path = models.CharField(max_length=512, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("cloning", "Cloning"),
            ("extracting", "Extracting"),
            ("analyzing", "Analyzing"),
            ("pending_cleanup", "Pending Cleanup"),
            ("cleaned", "Cleaned"),
            ("failed", "Failed"),
        ],
        default="cloning",
    )
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Clone {self.repo_url} - {self.status}"


class FileAnalysis(models.Model):
    """Lizard file-level code metrics."""

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="file_analyses",
    )
    commit = models.ForeignKey(
        Commit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="file_analyses",
    )

    file_path = models.CharField(max_length=1024)
    language = models.CharField(max_length=50)

    # Lizard metrics
    nloc = models.IntegerField(default=0)  # Lines of code (non-comment, non-blank)
    ccn = models.IntegerField(default=0)  # Cyclomatic complexity
    token_count = models.IntegerField(default=0)
    function_count = models.IntegerField(default=0)

    # Complexipy metrics (Python only)
    cognitive_complexity = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "File analyses"
        ordering = ["-ccn"]

    def __str__(self):
        return f"{self.file_path} (CCN: {self.ccn})"


class FunctionAnalysis(models.Model):
    """Lizard function-level code metrics."""

    file_analysis = models.ForeignKey(
        FileAnalysis,
        on_delete=models.CASCADE,
        related_name="functions",
    )

    function_name = models.CharField(max_length=512)
    long_name = models.CharField(max_length=1024)  # Full signature
    start_line = models.IntegerField()
    end_line = models.IntegerField()

    # Lizard metrics
    nloc = models.IntegerField(default=0)
    ccn = models.IntegerField(default=0)
    token_count = models.IntegerField(default=0)
    parameter_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Function analyses"
        ordering = ["-ccn"]

    def __str__(self):
        return f"{self.function_name} (CCN: {self.ccn})"
