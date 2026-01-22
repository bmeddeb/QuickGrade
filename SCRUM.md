# QuickGrade - Scrum Board

## Project Overview
- **Project**: QuickGrade
- **Goal**: Rewrite TaigaGitHubAudit with modern stack
- **Sprints**: 2-week cycles
- **Estimated Duration**: 6-8 sprints

---

## Epics

| ID | Epic | Description | Priority |
|----|------|-------------|----------|
| E1 | Project Setup | Django project, database, template integration | P0 |
| E2 | Authentication | GitHub OAuth, user management | P0 |
| E3 | GitHub Integration | Async fetch, models, data processing | P0 |
| E4 | GitHub Dashboard | Charts, tables, filters | P1 |
| E5 | Taiga Integration | Async fetch, models, data processing | P1 |
| E6 | Taiga Dashboard | Charts, tables, sprint views | P1 |
| E7 | Real-Time Updates | SSE, progress tracking, notifications | P1 |
| E8 | User Preferences | Palettes, settings, profile | P2 |
| E9 | Analytics | Gap detection, code complexity | P2 |
| E10 | CLI Interface | Management commands | P2 |
| E11 | File Upload | CSV/Excel import | P2 |
| E12 | Testing & Polish | Tests, docs, optimization | P3 |

---

## Sprint 1: Foundation (Week 1-2)

### Goals
- Django project scaffolding
- Database setup
- Template integration (fine-paper)
- Basic routing

### Tasks

#### E1: Project Setup

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E1-001 | Initialize Django project | Create `quickgrade` project with `manage.py` | 1h | TODO |
| E1-002 | Create core app | `python manage.py startapp core` | 0.5h | TODO |
| E1-003 | Create github_app | `python manage.py startapp github_app` | 0.5h | TODO |
| E1-004 | Create taiga_app | `python manage.py startapp taiga_app` | 0.5h | TODO |
| E1-005 | Setup pyproject.toml | Define dependencies, project metadata | 1h | TODO |
| E1-006 | Setup settings.py | Configure Django settings, environ | 2h | TODO |
| E1-007 | Setup .env.example | Document all environment variables | 0.5h | TODO |
| E1-008 | Setup PostgreSQL | Docker compose for local PostgreSQL | 1h | TODO |
| E1-009 | Setup Redis | Docker compose for local Redis | 0.5h | TODO |
| E1-010 | Configure Celery | Setup celery.py, tasks module | 2h | TODO |
| E1-011 | Copy fine-paper templates | Integrate layout-root.html as base.html | 2h | TODO |
| E1-012 | Setup Tailwind build | Configure tailwind.config.js, build script | 1h | TODO |
| E1-013 | Copy static assets | CSS, JS, fonts from fine-paper | 1h | TODO |
| E1-014 | Create base URL routing | urls.py for all apps | 1h | TODO |
| E1-015 | Create home page | Landing/dashboard selector page | 2h | TODO |

**Sprint 1 Total: ~16 hours**

---

## Sprint 2: Authentication (Week 3-4)

### Goals
- GitHub OAuth working
- User model and preferences
- Login/logout flow
- Profile page

### Tasks

#### E2: Authentication

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E2-001 | Install django-allauth | Add to dependencies, configure | 1h | TODO |
| E2-002 | Configure GitHub OAuth | Setup provider in settings, callback URLs | 2h | TODO |
| E2-003 | Create User model | Extend AbstractUser with github_id, avatar, etc. | 2h | TODO |
| E2-004 | Create UserPreferences model | Palettes, excluded_usernames, gap_threshold | 2h | TODO |
| E2-005 | Create login page | Template with GitHub OAuth button | 2h | TODO |
| E2-006 | Create logout view | Clear session, revoke token | 1h | TODO |
| E2-007 | Create profile page | Display user info, link to preferences | 3h | TODO |
| E2-008 | Create auth middleware | Protect routes requiring login | 1h | TODO |
| E2-009 | Store access token | Securely store GitHub token in user model | 1h | TODO |
| E2-010 | Test OAuth flow | End-to-end test of login/logout | 2h | TODO |

**Sprint 2 Total: ~17 hours**

---

## Sprint 3: GitHub Models & Fetch (Week 5-6)

### Goals
- All GitHub data models
- Async fetch service
- Basic data ingestion

### Tasks

#### E3: GitHub Integration - Models

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E3-001 | Create Repository model | All fields, FK to User | 1h | TODO |
| E3-002 | Create Collaborator model | GitHub user data | 1h | TODO |
| E3-003 | Create RepositoryCollaborator model | M2M with color | 1h | TODO |
| E3-004 | Create Branch model | Name, is_merged, is_default | 1h | TODO |
| E3-005 | Create Commit model | SHA, message, additions/deletions | 1h | TODO |
| E3-006 | Create PullRequest model | Title, state, dates, labels | 1h | TODO |
| E3-007 | Create CodeReview model | State, reviewer, body | 1h | TODO |
| E3-008 | Create Issue model | Title, state, labels | 1h | TODO |
| E3-009 | Create Comment model | Body, type, author | 1h | TODO |
| E3-010 | Create Notification model | Type, message, event_date | 1h | TODO |
| E3-011 | Run migrations | Create all tables | 0.5h | TODO |
| E3-012 | Create model admin | Register models in Django admin | 1h | TODO |

#### E3: GitHub Integration - Fetch Service

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E3-013 | Create base async client | httpx client wrapper with auth | 2h | TODO |
| E3-014 | Implement fetch_repository | Get repo metadata | 2h | TODO |
| E3-015 | Implement fetch_collaborators | Get collaborators, fallback to contributors | 2h | TODO |
| E3-016 | Implement fetch_branches | Get all branches | 1h | TODO |
| E3-017 | Implement fetch_commits | Paginated commit fetch | 3h | TODO |
| E3-018 | Implement fetch_pull_requests | Get PRs with reviews | 3h | TODO |
| E3-019 | Implement fetch_issues | Get issues with comments | 2h | TODO |
| E3-020 | Create fetch_all orchestrator | Concurrent fetch of multiple repos | 3h | TODO |
| E3-021 | Implement rate limit handling | Detect 403, exponential backoff | 2h | TODO |
| E3-022 | Implement data persistence | Save fetched data to models | 3h | TODO |
| E3-023 | Create Celery task | Background fetch task | 2h | TODO |

**Sprint 3 Total: ~35 hours**

---

## Sprint 4: GitHub Dashboard (Week 7-8)

### Goals
- Repository dashboard page
- Chart.js visualizations
- Data tables
- Filtering

### Tasks

#### E4: GitHub Dashboard

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E4-001 | Create dashboard layout | Template extending base.html | 2h | TODO |
| E4-002 | Create repository selector | Dropdown with user's repos | 2h | TODO |
| E4-003 | Create stats cards | Total commits, PRs, collaborators | 2h | TODO |
| E4-004 | Create date range picker | Alpine.js date filter component | 3h | TODO |
| E4-005 | Create collaborator filter | Multi-select collaborator filter | 2h | TODO |
| E4-006 | Implement commits line chart | Activity over time (Chart.js) | 3h | TODO |
| E4-007 | Implement commits bar chart | Commits per collaborator | 2h | TODO |
| E4-008 | Implement PR donut chart | PR state distribution | 2h | TODO |
| E4-009 | Implement contribution donut | Contribution by collaborator | 2h | TODO |
| E4-010 | Create commits table | Paginated, sortable, linked | 4h | TODO |
| E4-011 | Create PRs table | With state badges, labels | 3h | TODO |
| E4-012 | Create reviews table | Reviewer, state, date | 2h | TODO |
| E4-013 | Create API endpoints | JSON endpoints for charts/tables | 4h | TODO |
| E4-014 | Wire up Alpine.js | Reactive data binding | 3h | TODO |
| E4-015 | Add loading states | Skeleton loaders, spinners | 2h | TODO |

**Sprint 4 Total: ~38 hours**

---

## Sprint 5: Real-Time & Taiga Models (Week 9-10)

### Goals
- SSE progress streaming
- Toast notifications
- Taiga data models
- Taiga fetch service

### Tasks

#### E7: Real-Time Updates

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E7-001 | Create SSE endpoint | Django async streaming view | 3h | TODO |
| E7-002 | Create progress channel | Redis pub/sub for progress events | 2h | TODO |
| E7-003 | Implement progress tracking | Track fetch stages, percentages | 2h | TODO |
| E7-004 | Create JS event listener | Alpine.js SSE consumer | 2h | TODO |
| E7-005 | Create progress bar component | Visual progress indicator | 2h | TODO |
| E7-006 | Create toast component | Success/error/warning toasts | 2h | TODO |
| E7-007 | Wire up fetch UI | Start fetch, show progress, complete | 3h | TODO |

#### E5: Taiga Integration - Models

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E5-001 | Create Project model | Taiga project data | 1h | TODO |
| E5-002 | Create Member model | Project members | 1h | TODO |
| E5-003 | Create Sprint model | Milestones with dates, points | 1h | TODO |
| E5-004 | Create UserStory model | Stories with description | 1h | TODO |
| E5-005 | Create Task model | Tasks with status, assignment | 1h | TODO |
| E5-006 | Create TaskHistory model | Status change tracking | 1h | TODO |
| E5-007 | Run migrations | Create Taiga tables | 0.5h | TODO |

#### E5: Taiga Integration - Fetch

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E5-008 | Create Taiga async client | httpx client for Taiga API | 2h | TODO |
| E5-009 | Implement fetch_project | Get project by slug | 1h | TODO |
| E5-010 | Implement fetch_members | Get project members | 1h | TODO |
| E5-011 | Implement fetch_sprints | Get milestones | 2h | TODO |
| E5-012 | Implement fetch_tasks | Get tasks with history | 3h | TODO |
| E5-013 | Implement fetch_user_stories | Get user stories | 2h | TODO |
| E5-014 | Create fetch_all orchestrator | Concurrent project fetch | 2h | TODO |
| E5-015 | Implement data persistence | Save to models | 2h | TODO |
| E5-016 | Create Celery task | Background Taiga fetch | 1h | TODO |

**Sprint 5 Total: ~38 hours**

---

## Sprint 6: Taiga Dashboard & Preferences (Week 11-12)

### Goals
- Taiga dashboard
- Sprint/task visualizations
- User preferences UI

### Tasks

#### E6: Taiga Dashboard

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E6-001 | Create dashboard layout | Template with project selector | 2h | TODO |
| E6-002 | Create project selector | Dropdown with user's projects | 2h | TODO |
| E6-003 | Create sprint selector | Filter by sprint | 2h | TODO |
| E6-004 | Create stats cards | Tasks, completion rate, velocity | 2h | TODO |
| E6-005 | Implement burndown chart | Sprint burndown line chart | 3h | TODO |
| E6-006 | Implement task status chart | Donut chart by status | 2h | TODO |
| E6-007 | Implement member workload chart | Bar chart by member | 2h | TODO |
| E6-008 | Create tasks table | With status, assignment, sprint | 3h | TODO |
| E6-009 | Create task detail view | History, comments | 3h | TODO |
| E6-010 | Create API endpoints | JSON for charts/tables | 3h | TODO |

#### E8: User Preferences

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E8-001 | Create preferences page | Layout with sections | 2h | TODO |
| E8-002 | Create palette editor | Add/edit/delete color palettes | 4h | TODO |
| E8-003 | Create palette preview | Show colors visually | 1h | TODO |
| E8-004 | Create excluded usernames editor | List with add/remove | 2h | TODO |
| E8-005 | Create gap threshold setting | Number input with save | 1h | TODO |
| E8-006 | Create task colors editor | Color pickers for statuses | 2h | TODO |
| E8-007 | Create profile editor | Edit name, bio, location | 2h | TODO |
| E8-008 | Create preferences API | Save/load preferences | 2h | TODO |

**Sprint 6 Total: ~40 hours**

---

## Sprint 7: Analytics & CLI (Week 13-14)

### Goals
- Activity gap detection
- Code complexity analysis
- CLI management commands

### Tasks

#### E9: Analytics

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E9-001 | Create analytics service | Base analytics calculations | 2h | TODO |
| E9-002 | Implement commit analytics | Commits by author, over time | 2h | TODO |
| E9-003 | Implement PR analytics | Merge rate, lifecycle duration | 2h | TODO |
| E9-004 | Implement collaborator stats | Contribution percentages | 2h | TODO |
| E9-005 | Implement gap detection | Find gaps > threshold | 3h | TODO |
| E9-006 | Create notifications for gaps | Store gap notifications | 2h | TODO |
| E9-007 | Integrate Lizard | Code complexity analysis | 4h | TODO |
| E9-008 | Create FileInformation model | Store file metrics | 1h | TODO |
| E9-009 | Create FunctionInformation model | Store function metrics | 1h | TODO |
| E9-010 | Create complexity dashboard | Display metrics | 3h | TODO |

#### E10: CLI Interface

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E10-001 | Setup rich library | Pretty CLI output | 1h | TODO |
| E10-002 | Create auth commands | login, logout, status | 3h | TODO |
| E10-003 | Create fetch github command | Fetch repos from CLI | 3h | TODO |
| E10-004 | Create fetch taiga command | Fetch projects from CLI | 2h | TODO |
| E10-005 | Create fetch --file command | Import from CSV/Excel | 2h | TODO |
| E10-006 | Create export command | Export data to CSV/JSON | 3h | TODO |
| E10-007 | Create status command | Show fetch progress | 2h | TODO |
| E10-008 | Create repos list command | List fetched repos | 1h | TODO |
| E10-009 | Add progress bars | tqdm/rich progress display | 2h | TODO |
| E10-010 | Add JSON output option | --json flag for scripting | 1h | TODO |

**Sprint 7 Total: ~42 hours**

---

## Sprint 8: File Upload, Testing & Polish (Week 15-16)

### Goals
- File upload feature
- Comprehensive testing
- Documentation
- Performance optimization

### Tasks

#### E11: File Upload

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E11-001 | Create upload page | Drag-drop upload UI | 2h | TODO |
| E11-002 | Create upload endpoint | Handle file upload | 2h | TODO |
| E11-003 | Implement CSV parser | Extract slugs from CSV | 1h | TODO |
| E11-004 | Implement Excel parser | Extract slugs from Excel | 1h | TODO |
| E11-005 | Validate file structure | Check columns exist | 1h | TODO |
| E11-006 | Store slugs in session | Prepare for fetch | 1h | TODO |
| E11-007 | Redirect to fetch page | Start fetch after upload | 1h | TODO |

#### E12: Testing & Polish

| ID | Task | Description | Est | Status |
|----|------|-------------|-----|--------|
| E12-001 | Setup pytest | Configure pytest-django | 1h | TODO |
| E12-002 | Write model tests | Test all models | 4h | TODO |
| E12-003 | Write service tests | Test fetch services (mocked) | 4h | TODO |
| E12-004 | Write view tests | Test all views | 4h | TODO |
| E12-005 | Write API tests | Test JSON endpoints | 3h | TODO |
| E12-006 | Setup ruff linting | Code quality checks | 1h | TODO |
| E12-007 | Fix lint errors | Clean up code | 2h | TODO |
| E12-008 | Write README.md | Setup instructions, usage | 2h | TODO |
| E12-009 | Create docker-compose.yml | Full stack local dev | 2h | TODO |
| E12-010 | Optimize queries | select_related, prefetch_related | 3h | TODO |
| E12-011 | Add database indexes | Index frequently queried fields | 2h | TODO |
| E12-012 | Final QA testing | End-to-end testing | 4h | TODO |

**Sprint 8 Total: ~41 hours**

---

## Backlog (Future Sprints)

| ID | Task | Description | Priority |
|----|------|-------------|----------|
| BL-001 | Email notifications | Send email for activity gaps | P3 |
| BL-002 | Slack integration | Post notifications to Slack | P3 |
| BL-003 | PDF export | Export dashboards as PDF | P3 |
| BL-004 | Comparison view | Compare two repos/projects | P3 |
| BL-005 | Team management | Invite team members | P3 |
| BL-006 | Scheduled fetches | Auto-refresh data periodically | P3 |
| BL-007 | Webhook support | GitHub webhooks for real-time data | P3 |
| BL-008 | Dark mode | Theme toggle | P4 |
| BL-009 | Mobile app | React Native companion | P4 |
| BL-010 | API documentation | OpenAPI/Swagger docs | P3 |

---

## Definition of Done

A task is considered DONE when:

1. **Code Complete**: All code written and committed
2. **Tests Pass**: Unit tests written and passing
3. **Lint Clean**: No ruff/linter errors
4. **Reviewed**: Code reviewed (if pair/team)
5. **Documented**: Docstrings, comments where needed
6. **Deployed**: Works in development environment
7. **Accepted**: Meets acceptance criteria

---

## Sprint Ceremonies

### Daily Standup (if team)
- What did I do yesterday?
- What will I do today?
- Any blockers?

### Sprint Planning
- Review backlog
- Select tasks for sprint
- Estimate effort
- Commit to sprint goal

### Sprint Review
- Demo completed work
- Gather feedback
- Update backlog

### Sprint Retrospective
- What went well?
- What could improve?
- Action items

---

## Velocity Tracking

| Sprint | Planned | Completed | Notes |
|--------|---------|-----------|-------|
| 1 | 16h | - | Foundation |
| 2 | 17h | - | Auth |
| 3 | 35h | - | GitHub Models |
| 4 | 38h | - | GitHub Dashboard |
| 5 | 38h | - | Real-time + Taiga |
| 6 | 40h | - | Taiga Dashboard |
| 7 | 42h | - | Analytics + CLI |
| 8 | 41h | - | Testing + Polish |

**Total Estimated: ~267 hours**

---

## Task Status Legend

| Status | Description |
|--------|-------------|
| TODO | Not started |
| IN PROGRESS | Currently working |
| REVIEW | Needs review |
| BLOCKED | Waiting on dependency |
| DONE | Completed |

---

## How to Use This Board

### Starting a Task
1. Change status from `TODO` to `IN PROGRESS`
2. Create a feature branch: `git checkout -b E1-001-init-django`
3. Work on the task
4. Commit with task ID: `git commit -m "E1-001: Initialize Django project"`

### Completing a Task
1. Ensure Definition of Done is met
2. Create PR (if applicable)
3. Change status to `DONE`
4. Update velocity tracking

### Adding New Tasks
1. Assign to appropriate Epic
2. Give unique ID (Epic-Number)
3. Write clear description
4. Estimate effort
5. Add to appropriate sprint or backlog
