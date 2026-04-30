# Insighta Labs+ Backend API

Django REST API for the Insighta Labs+ Profile Intelligence System. The backend is the single source of truth for authentication, role enforcement, profile data, natural language search, CSV export, rate limiting, and audit logging.

## Live URL

- Backend: `https://rofile--ntegration-adewumijosephine3516-kodp7ruz.leapcell.dev`
- API docs: `/api/docs/`
- Health check: `/health/`

## System Architecture

```text
CLI client                  Web portal
Bearer JWT                  HTTP-only cookies
    |                            |
    +------------+---------------+
                 |
          Django REST API
          /api/v1/*
                 |
      Auth, RBAC, throttling,
      logging, API versioning
                 |
      Profile Intelligence API
      filters, sorting, NLP,
      pagination, CSV export
                 |
        PostgreSQL in production
        SQLite for local/CI
```

## Authentication Flow

The platform supports GitHub OAuth for browser users and a CLI OAuth exchange for terminal users.

Web flow:

1. User clicks "Continue with GitHub".
2. Browser opens `GET /auth/github`.
3. Backend generates `state`, `code_verifier`, and `code_challenge`.
4. Backend stores `oauth_state` and `code_verifier` in HttpOnly cookies.
5. Backend redirects to GitHub with PKCE and state.
6. GitHub redirects to `GET /auth/github/callback`.
7. Backend validates state and PKCE, creates or retrieves the user, issues tokens, and sets HttpOnly token cookies.

CLI flow:

1. `insighta login` generates `state`, `code_verifier`, and `code_challenge`.
2. The CLI opens the GitHub OAuth page and starts a temporary callback server.
3. The CLI validates `state` after the redirect.
4. The CLI sends `code`, `code_verifier`, and `code_challenge` to `/api/v1/auth/github/cli/`.
5. The backend validates PKCE, exchanges the GitHub code, creates or updates the user, and returns JWT tokens.

## Token Handling

- Access token lifetime: 3 minutes.
- Refresh token lifetime: 5 minutes.
- Refresh tokens rotate on refresh.
- Old refresh tokens are blacklisted after rotation.
- CLI credentials are stored locally at `~/.insighta/credentials.json`.

Auth endpoints:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/auth/github` | Start GitHub OAuth with PKCE and state |
| `GET` | `/auth/github/callback` | Validate OAuth callback and issue tokens |
| `POST` | `/auth/refresh` | Rotate refresh token and issue a new token pair |
| `POST` | `/auth/logout` | Blacklist refresh token and clear auth cookies |
| `GET` | `/api/users/me` | Return the authenticated user |

## Role Enforcement

Users have one of two roles:

| Role | Permissions |
| --- | --- |
| `admin` | Create, read, search, delete, and export profiles |
| `analyst` | Read and search profiles only |

Every profile endpoint requires authentication. Profile endpoints also require the `X-API-Version: 1` header.

Missing version header response:

```json
{
  "status": "error",
  "message": "API version header required"
}
```

## Profile API

Base path: `/api/profiles/`

Required header:

```http
X-API-Version: 1
```

Endpoints:

| Method | Endpoint | Role | Description |
| --- | --- | --- | --- |
| `GET` | `/api/profiles/` | analyst/admin | List profiles with filters, sorting, and pagination |
| `POST` | `/api/profiles/` | admin | Create a profile from a name |
| `GET` | `/api/profiles/{id}/` | authenticated | Retrieve one profile |
| `DELETE` | `/api/profiles/{id}/` | admin | Delete one profile |
| `GET` | `/api/profiles/search/?q=young males from nigeria` | analyst/admin | Natural language search |
| `GET` | `/api/profiles/export/?format=csv` | admin | Export filtered profiles as CSV |

Pagination response shape:

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "total_pages": 203,
  "links": {
    "self": "/api/profiles/?page=1&limit=10",
    "next": "/api/profiles/?page=2&limit=10",
    "prev": null
  },
  "data": []
}
```

Supported filters:

- `gender`
- `age_group`
- `country` or `country_id`
- `min_age`
- `max_age`
- `min_gender_probability`
- `min_country_probability`
- `sort_by=age|created_at|gender_probability`
- `order=asc|desc`

## Natural Language Parsing

Natural language search is rule-based, not LLM-based. The parser maps phrases into structured filters.

Examples:

| Query | Filters |
| --- | --- |
| `young males from nigeria` | `gender=male`, `min_age=16`, `max_age=24`, `country_id=NG` |
| `females above 30` | `gender=female`, `min_age=30` |
| `adult males from kenya` | `gender=male`, `age_group=adult`, `country_id=KE` |

## Rate Limiting and Logging

- Auth scope target: 10 requests per minute.
- Authenticated API users: 60 requests per minute.
- Each request is logged with method, endpoint, user id, status code, and response time.

## Local Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Environment variables:

```env
SECRET_KEY=replace-me
DEBUG=True
DATABASE_URL=postgres://user:password@host:5432/dbname
FRONTEND_URL=http://localhost:3000
GITHUB_CLIENT_ID=replace-me
GITHUB_CLIENT_SECRET=replace-me
GITHUB_CLI_CLIENT_ID=replace-me
GITHUB_CLI_CLIENT_SECRET=replace-me
```

If `DATABASE_URL` is omitted, the app uses local SQLite. Production should use PostgreSQL.

## CI/CD

GitHub Actions workflow: `.github/workflows/ci.yml`

Runs on pull requests and pushes to `main`:

- Install Python dependencies.
- Run `python manage.py check`.
- Run `python manage.py test`.

## Engineering Standards

- Use conventional commits, for example `feat(auth): add github oauth`.
- Create feature branches before opening PRs to `main`.
- All merges to `main` should pass CI.
