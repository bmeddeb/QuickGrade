# QuickGrade - System Requirements Document

> A modern rewrite of TaigaGitHubAudit with Django, async processing, and a lightweight frontend.

## 1. Project Overview

### 1.1 Purpose
A web application that aggregates and analyzes data from GitHub repositories and Taiga project management systems, providing real-time dashboards, team collaboration metrics, and activity insights.

### 1.2 Key Improvements Over Previous Version
- **Django** instead of Flask (batteries-included, admin, better async support)
- **Async/await** for concurrent API fetching (multiple repos/projects simultaneously)
- **Chart.js + Alpine.js + Tailwind 4.1** instead of Plotly Dash (lighter, faster)
- **~15 packages** instead of 104 dependencies
- **CLI support** for headless operation
- **Server-Sent Events (SSE)** for real-time updates (simpler than WebSockets)

### 1.3 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.x with async views |
| Database | PostgreSQL (prod), SQLite (dev) |
| Task Queue | Celery + Redis |
| Real-time | Server-Sent Events (SSE) |
| Frontend | Tailwind 4.1 + Alpine.js + Chart.js |
| Template | fine-paper dashboard template |
| Auth | django-allauth (GitHub OAuth) |
| API Clients | httpx (async) + PyGithub + python-taiga |

---

## 2. Functional Requirements

### 2.1 Authentication & User Management

#### FR-2.1.1 GitHub OAuth Authentication
- Users authenticate via GitHub OAuth 2.0
- Required scopes: `repo`, `user:email`
- Store access token securely for API calls
- Support token revocation on logout

#### FR-2.1.2 User Profile
| Field | Type | Description |
|-------|------|-------------|
| github_id | String | Unique GitHub identifier |
| username | String | GitHub username |
| email | String | User email |
| name | String | Display name |
| avatar_url | URL | Profile image |
| bio | Text | User bio |
| access_token | String | GitHub OAuth token (encrypted) |

#### FR-2.1.3 Session Management
- Django session framework
- Store active repository/project selections
- Handle session expiration gracefully

---

### 2.2 GitHub Integration

#### FR-2.2.1 Async Data Fetching
```python
# Concurrent fetching pattern
async def fetch_all_repos(repo_slugs: list[str], token: str):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_repo(client, slug, token) for slug in repo_slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### FR-2.2.2 Data Models

**Repository**
| Field | Type |
|-------|------|
| id | PK |
| name | String |
| full_name | String (owner/repo) |
| description | Text |
| created_at | DateTime |
| updated_at | DateTime |
| stars | Integer |
| forks | Integer |
| user | FK → User |

**Commit**
| Field | Type |
|-------|------|
| id | PK |
| sha | String (unique per repo) |
| message | Text |
| date | DateTime |
| additions | Integer |
| deletions | Integer |
| url | URL |
| is_merge | Boolean |
| repository | FK → Repository |
| author | FK → Collaborator |
| branch | FK → Branch |

**Branch**
| Field | Type |
|-------|------|
| id | PK |
| name | String (max 60) |
| is_merged | Boolean |
| is_default | Boolean |
| repository | FK → Repository |

**PullRequest**
| Field | Type |
|-------|------|
| id | PK |
| github_id | Integer |
| title | String |
| body | Text |
| state | Enum (open/closed/merged) |
| created_at | DateTime |
| merged_at | DateTime (nullable) |
| labels | JSONField |
| url | URL |
| repository | FK → Repository |
| creator | FK → Collaborator |
| branch | FK → Branch |

**CodeReview**
| Field | Type |
|-------|------|
| id | PK |
| github_id | Integer |
| state | Enum (APPROVED/COMMENTED/DISMISSED/PENDING) |
| body | Text |
| submitted_at | DateTime |
| pull_request | FK → PullRequest |
| reviewer | FK → Collaborator |

**Issue**
| Field | Type |
|-------|------|
| id | PK |
| github_id | Integer |
| title | String |
| body | Text |
| state | Enum (open/closed) |
| labels | JSONField |
| created_at | DateTime |
| repository | FK → Repository |
| creator | FK → Collaborator |

**Comment**
| Field | Type |
|-------|------|
| id | PK |
| github_id | Integer |
| body | Text |
| created_at | DateTime |
| comment_type | Enum (pr/issue/commit) |
| author | FK → Collaborator |
| pull_request | FK → PullRequest (nullable) |
| issue | FK → Issue (nullable) |

**Collaborator**
| Field | Type |
|-------|------|
| id | PK |
| github_id | Integer (unique) |
| username | String |
| full_name | String |
| email | String |
| avatar_url | URL |

**RepositoryCollaborator** (M2M through)
| Field | Type |
|-------|------|
| repository | FK → Repository |
| collaborator | FK → Collaborator |
| color | String (hex) |

#### FR-2.2.3 Rate Limiting & Error Handling
- Detect 403 rate limit responses
- Exponential backoff retry (3 attempts)
- Fall back to `/contributors` when `/collaborators` returns 403
- Progress reporting via SSE

---

### 2.3 Taiga Integration

#### FR-2.3.1 Async Data Fetching
```python
async def fetch_all_projects(project_slugs: list[str]):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_project(client, slug) for slug in project_slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### FR-2.3.2 Data Models

**Project**
| Field | Type |
|-------|------|
| id | PK |
| taiga_id | Integer |
| name | String |
| slug | String |
| description | Text |
| user | FK → User |

**Member**
| Field | Type |
|-------|------|
| id | PK |
| taiga_id | Integer |
| name | String |
| role | String |
| project | FK → Project |

**Sprint**
| Field | Type |
|-------|------|
| id | PK |
| taiga_id | Integer |
| name | String |
| start_date | Date |
| end_date | Date |
| total_points | Integer |
| closed_points | Integer |
| project | FK → Project |

**UserStory**
| Field | Type |
|-------|------|
| id | PK |
| taiga_id | Integer |
| name | String |
| description | Text |
| project | FK → Project |

**Task**
| Field | Type |
|-------|------|
| id | PK |
| taiga_id | Integer |
| ref | Integer |
| name | String |
| created_date | DateTime |
| finished_date | DateTime (nullable) |
| is_closed | Boolean |
| sprint | FK → Sprint |
| user_story | FK → UserStory (nullable) |
| assigned_to | FK → Member (nullable) |
| project | FK → Project |

**TaskHistory**
| Field | Type |
|-------|------|
| id | PK |
| event_date | DateTime |
| event_type | String |
| status_from | String |
| status_to | String |
| comment | Text |
| task | FK → Task |
| changed_by | FK → Member |

---

### 2.4 Analytics & Metrics

#### FR-2.4.1 Commit Analytics
- Commits per author (count, additions, deletions)
- Commit frequency over time (line chart)
- Activity timeline

#### FR-2.4.2 Pull Request Analytics
- PRs per author
- Merge rate percentage
- PR lifecycle duration
- State breakdown (open/closed/merged)

#### FR-2.4.3 Collaborator Statistics
- Contribution breakdown (commits, PRs, reviews, comments)
- Percentage distribution (donut chart)
- Workload comparison (bar chart)

#### FR-2.4.4 Activity Gap Detection
- Configurable threshold (default: 4 days)
- Notification generation for gaps
- Visual indicators on timeline

#### FR-2.4.5 Code Complexity (via Lizard)
- File metrics: NLOC, token count, cyclomatic complexity
- Function metrics: length, complexity, nesting level
- Languages: Python, JavaScript, Java, C/C++, TypeScript, Go

#### FR-2.4.6 Taiga Analytics
- Task completion rates per sprint
- Member workload distribution
- Sprint velocity tracking
- Burndown visualization

---

### 2.5 Dashboard & Visualization

#### FR-2.5.1 Layout (from fine-paper template)
```
┌─────────────────────────────────────────────────────────┐
│ Header: Search | Notifications | Profile               │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │  Main Content Area                          │
│          │  ┌─────────────┬─────────────┐              │
│ • Repos  │  │ Stats Card  │ Stats Card  │              │
│ • Taiga  │  ├─────────────┴─────────────┤              │
│ • Prefs  │  │ Line Chart (Activity)     │              │
│          │  ├─────────────┬─────────────┤              │
│          │  │ Donut Chart │ Bar Chart   │              │
│          │  ├─────────────┴─────────────┤              │
│          │  │ Data Table (paginated)    │              │
│          │  └───────────────────────────┘              │
│          │                                              │
├──────────┴──────────────────────────────────────────────┤
│ Footer                                                  │
└─────────────────────────────────────────────────────────┘
```

#### FR-2.5.2 Chart.js Components

**Line Charts**
- Commit activity over time
- PR activity over time
- Sprint burndown

**Bar Charts**
- Commits per collaborator
- PRs per collaborator
- Task completion by member

**Donut Charts**
- Contribution distribution
- PR state breakdown
- Task status breakdown

**Implementation Pattern (Alpine.js + Chart.js)**
```html
<div x-data="chartComponent()" x-init="initChart()">
  <canvas x-ref="chart"></canvas>
</div>

<script>
function chartComponent() {
  return {
    chart: null,
    initChart() {
      this.chart = new Chart(this.$refs.chart, {
        type: 'line',
        data: { /* fetched via API */ },
        options: { /* chart options */ }
      });
    }
  }
}
</script>
```

#### FR-2.5.3 Data Tables (Alpine.js)
- Sortable columns (click header)
- Pagination (10/25/50 per page)
- Search/filter
- Links to GitHub/Taiga

#### FR-2.5.4 Filters
- Date range picker
- Repository/Project selector
- Collaborator/Member filter

---

### 2.6 Real-Time Updates

#### FR-2.6.1 Server-Sent Events (SSE)
```python
# Django async view
async def progress_stream(request):
    async def event_generator():
        async for progress in fetch_progress_channel():
            yield f"data: {json.dumps(progress)}\n\n"

    return StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
```

```javascript
// Frontend (Alpine.js)
const eventSource = new EventSource('/api/progress/');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  this.progress = data.percentage;
  this.message = data.message;
};
```

#### FR-2.6.2 Progress Events
| Event | Data |
|-------|------|
| `fetch_started` | `{total: N, type: 'github'|'taiga'}` |
| `repo_progress` | `{current: N, total: M, repo: 'name', stage: 'commits'}` |
| `repo_complete` | `{repo: 'name', success: true}` |
| `fetch_complete` | `{total: N, failed: M}` |
| `error` | `{message: 'error text', repo: 'name'}` |

#### FR-2.6.3 Toast Notifications
- Success (green)
- Warning (yellow)
- Error (red)
- Info (blue)

---

### 2.7 User Preferences

#### FR-2.7.1 Preferences Model
```python
class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Color palettes (JSON array of {id, name, colors[]})
    palettes = models.JSONField(default=list)
    active_palette_id = models.CharField(max_length=36, blank=True)

    # Excluded usernames (for filtering bots, etc.)
    excluded_usernames = models.JSONField(default=list)

    # Activity gap threshold (days)
    gap_threshold = models.IntegerField(default=4)

    # Taiga task status colors
    task_colors = models.JSONField(default=dict)
```

#### FR-2.7.2 Default Palettes
```python
DEFAULT_PALETTES = [
    {'id': 'default', 'name': 'Default', 'colors': ['#51cbce', '#fbc658', '#ef8157', '#6bd098', '#51bcda']},
    {'id': 'paper', 'name': 'Paper', 'colors': ['#f96332', '#66615b', '#51cbce', '#6bd098', '#fbc658']},
]
```

#### FR-2.7.3 Default Excluded Usernames
```python
DEFAULT_EXCLUDED = ['root', 'Local Administrator', 'Administrator', 'dependabot[bot]']
```

---

### 2.8 File Upload

#### FR-2.8.1 Supported Formats
- CSV (.csv)
- Excel (.xlsx, .xls)

#### FR-2.8.2 Expected Structure
| Column A | Column B |
|----------|----------|
| GitHub repo slug (owner/repo) | Taiga project slug |
| owner1/repo1 | project-slug-1 |
| owner2/repo2 | project-slug-2 |

#### FR-2.8.3 Processing Flow
1. Upload file
2. Validate format
3. Extract slugs
4. Store in session
5. Redirect to fetch page
6. Begin async fetch

---

### 2.9 CLI Interface

#### FR-2.9.1 Management Commands
```bash
# Authentication
python manage.py auth login       # Open browser for OAuth
python manage.py auth logout      # Clear stored token
python manage.py auth status      # Show current user

# Fetching
python manage.py fetch github owner/repo1 owner/repo2 --concurrent=5
python manage.py fetch taiga project-slug-1 project-slug-2 --concurrent=3
python manage.py fetch --file repos.csv

# Export
python manage.py export owner/repo --format=csv --output=./export/
python manage.py export owner/repo --format=json

# Analysis
python manage.py analyze owner/repo --type=complexity
python manage.py analyze owner/repo --gaps --threshold=7

# Status
python manage.py status           # Show fetch progress
python manage.py repos list       # List fetched repos
python manage.py repos delete owner/repo
```

#### FR-2.9.2 Output
- Progress bars (tqdm or rich)
- Colored output
- JSON output option (`--json`)
- Verbose mode (`-v`, `-vv`)

---

## 3. Non-Functional Requirements

### 3.1 Performance
- Async I/O for all external API calls
- Connection pooling (httpx)
- Database query optimization (select_related, prefetch_related)
- Pagination for large datasets

### 3.2 Scalability
- Celery for background tasks
- Redis for caching and message broker
- PostgreSQL for production

### 3.3 Security
- CSRF protection (Django default)
- SQL injection prevention (ORM)
- XSS prevention (template escaping)
- Encrypted token storage

### 3.4 Reliability
- Retry logic with exponential backoff
- Graceful degradation on API failures
- Transaction management

---

## 4. Project Structure

```
QuickGrade/
├── manage.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── README.md
│
├── quickgrade/                 # Django project
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── celery.py
│
├── core/                       # Core app (users, auth)
│   ├── models.py              # User, UserPreferences
│   ├── views.py               # Auth views, profile
│   ├── urls.py
│   └── management/
│       └── commands/          # CLI commands
│
├── github_app/                 # GitHub integration
│   ├── models.py              # Repository, Commit, PR, etc.
│   ├── views.py               # Dashboard, API endpoints
│   ├── services.py            # Async fetch logic
│   ├── analytics.py           # Analytics calculations
│   └── urls.py
│
├── taiga_app/                  # Taiga integration
│   ├── models.py              # Project, Sprint, Task, etc.
│   ├── views.py               # Dashboard, API endpoints
│   ├── services.py            # Async fetch logic
│   ├── analytics.py           # Analytics calculations
│   └── urls.py
│
├── templates/                  # Django templates
│   ├── base.html              # From fine-paper layout-root
│   ├── auth/
│   │   ├── login.html
│   │   └── profile.html
│   ├── github/
│   │   ├── dashboard.html
│   │   └── partials/          # Alpine.js components
│   ├── taiga/
│   │   └── dashboard.html
│   └── components/            # Reusable components
│       ├── charts.html
│       ├── tables.html
│       └── cards.html
│
├── static/
│   ├── css/
│   │   └── app.css            # Compiled Tailwind
│   ├── js/
│   │   ├── app.js             # Alpine components
│   │   └── charts.js          # Chart.js setup
│   └── img/
│
└── tasks/                      # Celery tasks
    ├── __init__.py
    ├── github.py
    └── taiga.py
```

---

## 5. Dependencies

### 5.1 Python Packages (pyproject.toml)
```toml
[project]
name = "quickgrade"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    # Django
    "django>=5.0",
    "django-allauth>=0.60",
    "django-environ>=0.11",

    # Database
    "psycopg[binary]>=3.1",

    # Async HTTP
    "httpx>=0.27",

    # Task Queue
    "celery>=5.3",
    "redis>=5.0",

    # API Clients
    "PyGithub>=2.1",
    "python-taiga>=1.3",

    # Data Processing
    "pandas>=2.1",
    "openpyxl>=3.1",        # Excel support

    # Code Analysis
    "lizard>=1.17",

    # CLI
    "rich>=13.0",           # Pretty CLI output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.5",
    "pytest-asyncio>=0.23",
    "ruff>=0.1",
]
```

### 5.2 Frontend (package.json)
```json
{
  "devDependencies": {
    "tailwindcss": "^4.1.0",
    "@tailwindcss/cli": "^4.1.0"
  },
  "dependencies": {
    "alpinejs": "^3.13.5",
    "chart.js": "^4.5.1"
  }
}
```

### 5.3 Total: ~15 Python packages (vs 104 previously)

---

## 6. API Endpoints

### 6.1 Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/login/` | Redirect to GitHub OAuth |
| GET | `/auth/callback/` | OAuth callback |
| POST | `/auth/logout/` | Logout |
| GET | `/auth/profile/` | User profile page |

### 6.2 GitHub
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/github/` | Dashboard |
| GET | `/github/repos/` | List repositories |
| POST | `/github/fetch/` | Start fetch (accepts JSON or form) |
| GET | `/github/progress/` | SSE progress stream |
| GET | `/github/api/stats/<repo>/` | Repository stats JSON |
| GET | `/github/api/commits/<repo>/` | Commits JSON (paginated) |
| GET | `/github/api/prs/<repo>/` | Pull requests JSON |
| GET | `/github/api/charts/<repo>/` | Chart data JSON |

### 6.3 Taiga
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/taiga/` | Dashboard |
| GET | `/taiga/projects/` | List projects |
| POST | `/taiga/fetch/` | Start fetch |
| GET | `/taiga/progress/` | SSE progress stream |
| GET | `/taiga/api/stats/<project>/` | Project stats JSON |
| GET | `/taiga/api/tasks/<project>/` | Tasks JSON |
| GET | `/taiga/api/charts/<project>/` | Chart data JSON |

### 6.4 Preferences
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/preferences/` | Preferences page |
| POST | `/preferences/palettes/` | Save palettes |
| POST | `/preferences/excluded/` | Save excluded usernames |
| POST | `/preferences/gap/` | Save gap threshold |

### 6.5 Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/upload/` | Upload page |
| POST | `/upload/` | Process uploaded file |

---

## 7. Migration Plan

### 7.1 Phase 1: Setup
- [ ] Initialize Django project
- [ ] Configure django-allauth for GitHub OAuth
- [ ] Copy fine-paper templates and static files
- [ ] Set up Tailwind build

### 7.2 Phase 2: Core
- [ ] User model and preferences
- [ ] Authentication views
- [ ] Base templates

### 7.3 Phase 3: GitHub Integration
- [ ] GitHub models
- [ ] Async fetch services
- [ ] Dashboard views
- [ ] Chart.js integration

### 7.4 Phase 4: Taiga Integration
- [ ] Taiga models
- [ ] Async fetch services
- [ ] Dashboard views

### 7.5 Phase 5: Real-time
- [ ] SSE endpoints
- [ ] Progress tracking
- [ ] Toast notifications

### 7.6 Phase 6: CLI
- [ ] Management commands
- [ ] Rich output formatting

### 7.7 Phase 7: Polish
- [ ] Testing
- [ ] Documentation
- [ ] Performance optimization

---

## 8. Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/quickgrade

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret

# Taiga (optional, for API access)
TAIGA_API_URL=https://api.taiga.io/api/v1

# Workers
GITHUB_CONCURRENT_LIMIT=5
TAIGA_CONCURRENT_LIMIT=3
```

---

## 9. Template Reference (fine-paper)

### 9.1 Key Files to Copy
```
fine-paper/
├── templates/
│   └── layout-root.html    → templates/base.html
├── assets/
│   ├── app.css             → static/css/app.css
│   ├── app.js              → static/js/app.js
│   └── nucleo.css          → static/css/nucleo.css
├── src/
│   └── app.css             → src/app.css (Tailwind source)
└── tailwind.config.js      → tailwind.config.js
```

### 9.2 Color Palette (from tailwind.config.js)
```css
--paper-bg: #f4f3ef
--paper-card: #ffffff
--paper-text: #252422
--paper-sidebar: #66615b
--paper-primary: #51cbce
--paper-info: #51bcda
--paper-success: #6bd098
--paper-warning: #fbc658
--paper-danger: #ef8157
--paper-orange: #f96332
```

### 9.3 Alpine.js Patterns
- `x-data="layout()"` - Layout state (sidebar, mobile menu)
- `x-data="collapse()"` - Collapsible sections
- `x-show`, `x-transition` - Show/hide with animation
- `@click.outside` - Close dropdowns
