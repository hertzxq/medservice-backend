# MedService Backend - Project Guide

## Business Context

**Goal**: Build a review collection service for medical clinics targeting >7–10% conversion (above competitors). Patient motivation is built on promotions and promo codes (win-win). Outreach is initiated by the system, not the patient. MVP deadline — April.

**Target audience and roles**:
- **Patient** — receives SMS (timezone-aware), leaves a rating.
- **Client (Clinic)** — manages branches, motivational offers, and blacklist.
- **Admin (System)** — administers clinics, accounts, global settings.

**MVP Scope & Constraints**:
- **Delivery**: SMS and Email. Messenger integrations (Telegram, WhatsApp) and CRM are **not in MVP**.
- **SMS and personal data**: First SMS is sent without using personal data without consent. Consent to personal data processing is requested at step 2 of the funnel. Legal responsibility for data processing lies with the clinic.
- **Load**: Starting with 1 client (up to 10 clinics), possible growth to large clients with 300+ branches. Scalable architecture.

---

## Technical Overview

**Feedback AI** backend on FastAPI for managing reviews, complaints, and patient requests for medical branches.

### Core Features
- JWT authentication for the admin panel.
- RBAC authorization: mutations (`POST /requests`) require superuser privileges.
- Analytics per branch and across all branches with period filters.
- Extended analytics (dashboard): platforms, satisfaction, NPS series, employee ratings, recent reviews.
- Published review management (filters by platform/rating).
- Intercepted complaint handling (list + mark `resolved`).
- Monitoring statuses of sent review requests.
- Branch settings management: request frequency, email notifications, specialization.
- Employee CRUD (platform profile management).
- Blacklist CRUD (exclude clients from review requests).

### Scope Boundary
- SMS/email sending and external integrations are intentionally left as stubs.
- Backend stores and serves data but does not perform real message delivery.

---

## Technology Stack

- **Python 3.12+** — runtime.
- **FastAPI 0.115** — HTTP API and OpenAPI/Swagger.
- **SQLAlchemy 2.0** — ORM and PostgreSQL access.
- **PostgreSQL 16** — primary database.
- **Alembic** — schema migrations.
- **Pydantic v2** + **pydantic-settings** — validation, serialization, configuration.
- **python-jose + bcrypt** — JWT and password hashing.
- **Poetry** — dependencies and task runner.
- **pytest + httpx** — testing.
- **black, ruff, mypy** — linting and typing (dev).

---

## Architecture Patterns

### Project Structure

```
medservice-backend/
├── app/
│   ├── api/v1/           # REST endpoints
│   │   ├── router.py     # Main router, assembles all modules
│   │   ├── auth.py       # Authentication and JWT
│   │   ├── analytics.py  # Analytics (basic + dashboard)
│   │   ├── branches.py   # Branches (GET + PATCH)
│   │   ├── reviews.py    # Published reviews
│   │   ├── complaints.py # Intercepted complaints
│   │   ├── requests.py   # Review requests
│   │   ├── employees.py  # Employee CRUD
│   │   └── blacklist.py  # Blacklist CRUD
│   ├── core/
│   │   ├── database.py   # SessionLocal, Base, get_db
│   │   ├── dependencies.py # get_current_user, require_superuser
│   │   └── security.py   # JWT create/decode, bcrypt hash/verify
│   ├── models/           # SQLAlchemy models
│   │   ├── user.py
│   │   ├── branch.py     # + settings: timezone, emails, frequency
│   │   ├── review.py
│   │   ├── complaint.py
│   │   ├── request.py
│   │   ├── employee.py   # Branch employees
│   │   └── blacklist.py  # Client blacklist
│   ├── schemas/          # Pydantic schemas
│   │   ├── common.py     # APIModel (camelCase alias generator)
│   │   ├── auth.py
│   │   ├── analytics.py
│   │   ├── branch.py     # BranchResponse, BranchUpdate, BranchesListResponse
│   │   ├── review.py
│   │   ├── complaint.py
│   │   ├── request.py
│   │   ├── user.py
│   │   ├── employee.py   # EmployeeBase/Create/Update/Response
│   │   └── blacklist.py  # BlacklistUserBase/Create/Update/Response
│   ├── config.py         # Settings from .env (Pydantic Settings)
│   └── main.py           # FastAPI app entrypoint
├── alembic/
│   └── versions/         # Migrations
├── tests/                # pytest tests
│   ├── conftest.py       # Fixtures: TestClient, DB, auth
│   ├── test_auth_api.py
│   ├── test_analytics_api.py
│   ├── test_branches_api.py
│   ├── test_complaints_api.py
│   ├── test_requests_api.py
│   └── test_reviews_api.py
├── seed.py               # Seed test data
├── docker-compose.yml    # PostgreSQL container
└── pyproject.toml        # Poetry: dependencies, dev tools
```

### API Naming Contract

- Python code uses `snake_case` fields (`avg_rating`, `branch_id`).
- HTTP JSON responses and requests support `camelCase` (`avgRating`, `branchId`) via base schema `app/schemas/common.py` (`APIModel`).
- Frontend works **without additional mapping** — serialization/deserialization is transparent.

---

## Authentication Flow

### Endpoints
- `POST /api/v1/auth/login` — login by `username/password`, returns JWT + user data.
- `GET /api/v1/auth/me` — current user via Bearer token.
- `POST /api/v1/auth/forgot-password` — password recovery stub. Always 200 OK (enumeration protection).

### JWT
- Algorithm: `HS256`.
- Lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 min).
- Token expected in `Authorization: Bearer <token>`.
- Password hashing: `bcrypt` (directly via `bcrypt` library, no passlib).

---

## Domain Endpoints

### Branches

- `GET /api/v1/branches`
  - Returns list of all branches.
  - Format: `{ branches: [...], total: number }`.
  - Each branch includes settings: `timezone`, `specialization`, `requestFrequencyDays`, `complaintEmails`, `reminderEmails`.

- `PATCH /api/v1/branches/{branchId}`
  - Partial update of branch settings.
  - Body: `BranchUpdate` (all fields optional).
  - Returns: updated `BranchResponse`.

### Analytics

- `GET /api/v1/analytics/{branchId}?period=week|30|90|year`
  - Basic branch metrics: `{ sent, reviews, complaints, avgRating }`.

- `GET /api/v1/analytics/{branchId}/dashboard?period=week|30|90|year`
  - Extended dashboard payload:
  - `periodStart`, `periodEnd` — period boundaries.
  - `platforms` — platform table: rating, reviews, negative count.
  - `satisfaction` — distribution by stars (5→1).
  - `npsSmall`, `npsLarge` — NPS timeline (7 and 12 points).
  - `employees` — employee ratings (extracted from review text).
  - `recentReviews` — latest reviews.

- `GET /api/v1/analytics/branches?period=week|30|90|year`
  - Table across all branches:
  - `{ rows: [{ id, name, requests, newReviews, interceptedComplaints, avgRating, nps }] }`.

### Reviews
- `GET /api/v1/reviews`
  - Filters: `branchId`, `platform`, `ratingMin`, `ratingMax`, `period`, `limit`, `offset`.
  - Returns: `{ reviews: [...], total }`.

### Complaints
- `GET /api/v1/complaints`
  - Filters: `branchId`, `resolved`, `limit`, `offset`.
  - Returns: `{ complaints: [...], total }`.
- `PATCH /api/v1/complaints/{complaintId}`
  - Body: `{ resolved: boolean }`.

### Requests
- `GET /api/v1/requests`
  - Filters: `branchId`, `status`, `limit`, `offset`.
  - Returns: `{ requests: [...], total }`.
- `POST /api/v1/requests` **(requires superuser)**
  - Creates a review request. `request_link` = UUID.
  - Real SMS sending — stub.

### Employees
- `GET /api/v1/employees?branch_id={branchId}` — branch employee list.
- `POST /api/v1/employees?branch_id={branchId}` — create employee: `{ name, active, profiles }`.
- `PATCH /api/v1/employees/{employeeId}` — partial update: `{ name?, active?, profiles? }`.
- `DELETE /api/v1/employees/{employeeId}` — delete employee. 204 No Content.

### Blacklist
- `GET /api/v1/blacklist?branch_id={branchId}` — branch blacklist.
- `POST /api/v1/blacklist?branch_id={branchId}` — add: `{ lastName, firstName, phone, reason? }`.
- `PATCH /api/v1/blacklist/{userId}` — partial update: `{ lastName?, firstName?, phone?, reason? }`.
- `DELETE /api/v1/blacklist/{userId}` — remove from blacklist. 204 No Content.

### Utility Endpoints
- `GET /` — service info.
- `GET /health` — health check `{ status: "ok" }`.

---

## Data Model

### Main Entities

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | System admins (username, email, bcrypt hash, is_superuser) |
| `Branch` | `branches` | Clinic branches with settings |
| `Review` | `reviews` | Published reviews. Indexes: `platform`, `published_at` |
| `Complaint` | `complaints` | Intercepted complaints. Indexes: `resolved`, `created_at` |
| `Request` | `requests` | Patient requests. Indexes: `status`, `sent_at`. Unique: `request_link` |
| `Employee` | `employees` | Branch employees (name, active, profiles JSON) |
| `BlacklistUser` | `blacklist_users` | Clients excluded from requests (last name, first name, phone, reason) |

### Branch Settings Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timezone` | `String` | `"Moscow time - UTC +3"` | Timezone |
| `specialization` | `String` | `"Ophthalmology"` | Area of activity |
| `request_frequency_days` | `Integer` | `14` | Repeat request frequency (days) |
| `complaint_emails` | `JSON` | `[]` | Emails for complaints |
| `reminder_emails` | `JSON` | `[]` | Emails for reminders |

### Relationships

- `Branch` → `Review`, `Complaint`, `Request`, `Employee`, `BlacklistUser` (cascade delete).
- `Employee.branch_id` → `Branch.id` (FK, indexed).
- `BlacklistUser.branch_id` → `Branch.id` (FK, indexed).

### Constraints
- `Request`: status `published` requires `published_at IS NOT NULL`.
- `Request`: `review_id` and `complaint_id` cannot both be set simultaneously.

### Enums
- `PlatformEnum`: `yandex_maps`, `google_maps`, `2gis`, `prodoctorov`, `napopravku`, `other`.
- `RequestStatusEnum`: `sent`, `opened`, `rated`, `visited`, `published`, `complaint`.

---

## Development Workflow

### Local Setup

```bash
cd medservice-backend
cp .env.example .env          # Fill in DATABASE_URL, SECRET_KEY
poetry install
docker-compose up -d          # PostgreSQL (vars: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
poetry run alembic upgrade head
poetry run python seed.py     # Creates admin + test data
poetry run python app/main.py # Run via uvicorn (host/port from .env)
```

### API Docs
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### First Login
- Dashboard (`/login`): `user` / `12345678` (regular user)
- Admin panel (`/admin/login`): `admin` / `12345678` (superuser)
- Change passwords before using in production.

### Running Tests

```bash
poetry run pytest tests/ -v
```

Tests use `httpx.AsyncClient` + `TestClient`, a separate in-memory database, and fixtures from `conftest.py`.

---

## Configuration (`app/config.py`)

Settings loaded from `.env` via `pydantic-settings`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | Yes | — | JWT key (change in prod!) |
| `DEBUG` | No | `false` | Enable debug mode |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Token TTL |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | JSON array or comma-separated string |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `DATABASE_ECHO` | No | `false` | SQL query logging |

### CORS
- Accepts JSON array: `["http://localhost:3000"]`
- Or comma-separated string: `http://localhost:3000,https://example.com`

---

## Frontend Integration Notes

- Backend periods: `week | 30 | 90 | year`.
- JSON fields are `camelCase`, transparent replacement of mock API without mapping.
- Analytics and filter query parameters match frontend types.
- Delivery channels (SMS/email/messengers) are out of scope.
- `PATCH /branches/{id}` maps to frontend `updateBranch()`.
- Employee and blacklist CRUD maps to settings page and blacklist page.
