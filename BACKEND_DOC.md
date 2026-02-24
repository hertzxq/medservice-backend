# MedService Backend - Project Guide

## Project Overview

**Feedback AI (Фидбэк ИИ)** backend на FastAPI для управления отзывами, жалобами и запросами клиентов медицинских филиалов.

### Core Features
- JWT-аутентификация для админ-панели.
- RBAC-авторизация: мутации (`PATCH /complaints`, `POST /requests`) требуют прав суперпользователя.
- Аналитика по филиалу и по всем филиалам с фильтрами периода.
- Управление опубликованными отзывами (фильтры по платформе/рейтингу).
- Работа с перехваченными жалобами (список + отметка `resolved`).
- Мониторинг статусов отправленных запросов на отзыв.

### Scope Boundary
- Отправка SMS/email и внешние интеграции намеренно оставлены заглушками.
- Backend хранит и отдает данные, но не выполняет реальную доставку сообщений.

---

## Technology Stack

- **FastAPI 0.115** - HTTP API и OpenAPI/Swagger.
- **SQLAlchemy 2.0** - ORM и доступ к PostgreSQL.
- **PostgreSQL 16** - основная БД.
- **Alembic** - миграции схемы.
- **Pydantic v2** - валидация и сериализация схем.
- **python-jose + passlib** - JWT и bcrypt.
- **Poetry** - зависимости и запуск.

---

## Architecture Patterns

### API Layers

```
medservice-backend/
├── app/
│   ├── api/v1/           # REST endpoints
│   ├── core/             # БД, security, dependencies
│   ├── models/           # SQLAlchemy модели
│   ├── schemas/          # Pydantic схемы
│   ├── config.py         # Settings из .env
│   └── main.py           # FastAPI app entrypoint
├── alembic/
│   └── versions/         # Миграции
└── seed.py               # Заполнение тестовыми данными
```

### API Naming Contract

- В коде Python используются `snake_case` поля (`avg_rating`, `branch_id`).
- В HTTP JSON ответы и запросы поддерживают `camelCase` (`avgRating`, `branchId`) для совместимости с frontend.
- Это реализовано через базовую схему `app/schemas/common.py`.

---

## Authentication Flow

### Endpoints
- `POST /api/v1/auth/login` - вход по `username/password`, возвращает JWT.
- `GET /api/v1/auth/me` - текущий пользователь по Bearer токену.
- `POST /api/v1/auth/forgot-password` - заглушка восстановления пароля (без реальной отправки email). Всегда возвращает 200 OK (защита от перечисления пользователей).

### JWT
- Алгоритм: `HS256`.
- Время жизни токена: `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Токен ожидается в `Authorization: Bearer <token>`.

---

## Domain Endpoints

### Branches
- `GET /api/v1/branches`
  - Возвращает филиалы для селектора/настроек.
  - Формат: `{ branches: [...], total: number }`.

### Analytics
- `GET /api/v1/analytics/{branchId}?period=week|30|90|year`
  - Возвращает метрики филиала:
  - `{ sent, reviews, complaints, avgRating }`
- `GET /api/v1/analytics/branches?period=week|30|90|year`
  - Таблица по всем филиалам:
  - `{ rows: [{ id, name, requests, newReviews, interceptedComplaints, avgRating, nps }] }`

### Reviews
- `GET /api/v1/reviews`
  - Фильтры:
  - `branchId`, `platform`, `ratingMin`, `ratingMax`, `period`, `limit`, `offset`.
  - Возвращает: `{ reviews: [...], total }`.

### Complaints
- `GET /api/v1/complaints`
  - Фильтры:
  - `branchId`, `resolved`, `limit`, `offset`.
  - Возвращает: `{ complaints: [...], total }`.
- `PATCH /api/v1/complaints/{complaintId}`
  - Тело: `{ resolved: boolean }`.

### Requests
- `GET /api/v1/requests`
  - Фильтры:
  - `branchId`, `status`, `limit`, `offset`.
  - Возвращает: `{ requests: [...], total }`.
- `POST /api/v1/requests` **(требует superuser)**
  - Создает запрос на отзыв и возвращает tracking-данные.
  - `request_link` генерируется как уникальный UUID (`uuid4`).
  - Реальная отправка SMS не выполняется (оставлено как stub).

---

## Data Model

### Main Entities
- `User` - администраторы системы.
- `Branch` - филиалы клиники.
- `Review` - опубликованные отзывы. Индексы: `platform`, `published_at`.
- `Complaint` - перехваченные негативные оценки/жалобы. Индексы: `resolved`, `created_at`.
- `Request` - отправки клиентам с трекингом статуса воронки. Индексы: `status`, `sent_at`. Уникальное поле: `request_link`.

### Constraints
- `Request`: статус `published` требует `published_at IS NOT NULL`.
- `Request`: `review_id` и `complaint_id` не могут быть оба заполнены одновременно.

### Enums
- `PlatformEnum`: `yandex_maps`, `google_maps`, `2gis`, `prodoctorov`, `napopravku`, `other`.
- `RequestStatusEnum`: `sent`, `opened`, `rated`, `visited`, `published`, `complaint`.

---

## Development Workflow

### Local Setup

```bash
cd medservice-backend
cp .env.example .env
poetry install
docker-compose up -d          # Требует переменных POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB (см. docker-compose.yml)
poetry run alembic upgrade head
poetry run python seed.py
poetry run uvicorn app.main:app --reload
```

### API Docs
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### First Login
- `username: admin`
- `password: MedSvc!Adm1n_2024`
- ⚠️ Смените пароль перед использованием в production.

---

## Configuration Notes

### Docker / PostgreSQL
- `docker-compose.yml` читает пароль из переменных окружения: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- Дефолтные значения указаны в файле, но **должны быть заменены** в production.

### CORS
- `CORS_ORIGINS` можно задавать:
  - JSON-массивом: `["http://localhost:3000"]`
  - или строкой через запятую: `http://localhost:3000,https://example.com`

### Environment
- `DATABASE_URL` обязателен.
- `SECRET_KEY` обязателен и должен быть изменен в production.

---

## Frontend Integration Notes

- Backend соответствует frontend-периодам: `week | 30 | 90 | year`.
- JSON-поля отдаются в `camelCase`, чтобы заменить mock API без дополнительного маппинга.
- Для аналитики и фильтров можно использовать те же query-параметры, что в frontend типах.
- Каналы доставки (SMS/email/мессенджеры) intentionally out-of-scope в текущей реализации.
