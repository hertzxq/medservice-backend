# MedService Backend API

REST API for managing medical clinic reviews.

## Stack

- FastAPI 0.115
- PostgreSQL + SQLAlchemy
- JWT Authentication
- Alembic migrations
- Poetry dependency management

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Start PostgreSQL
docker-compose up -d

# 3. Apply migrations
poetry run alembic upgrade head

# 4. Seed test data
poetry run python seed.py

# 5. Start server
poetry run uvicorn app.main:app --reload
```

## Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Test Credentials

- **Dashboard (`/login`):** `user` / `12345678` (regular user)
- **Admin panel (`/admin/login`):** `admin` / `12345678` (superuser)
