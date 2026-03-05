# MedService Backend - Project Guide

## Business Context & ТЗ (Техническое Задание)

**Цель проекта**: Создать сервис сбора отзывов для медицинских клиник с конверсией >7-10% (выше конкурентов). Мотивация пациентов строится на акциях и промокодах (win-win). Инициатива исходит от системы, а не пациента. Дедлайн MVP — апрель.

**Целевая аудитория и роли**:
- **Пациент** — получает SMS (с учетом часового пояса), оставляет оценку.
- **Клиент (Клиника)** — управляет филиалами, мотивирующими офферами и черным списком.
- **Admin (System)** — администрирует клиники, аккаунты, глобальные настройки.

**MVP Scope & Constraints**:
- **Доставка**: SMS и Email. Интеграции с мессенджерами (Telegram, WhatsApp) и CRM в MVP **не входят**.
- **SMS и ПД**: При первой отправке SMS персональные данные не используются без согласия. Согласие на обработку ПД запрашивается на втором шаге воронки. Юридическая ответственность за обработку данных лежит на клинике.
- **Нагрузка**: Старт с 1 клиента (до 10 клиник), возможен рост до крупных клиентов с 300+ филиалами. Масштабируемая архитектура.

---

## Technical Overview

**Feedback AI (Фидбэк ИИ)** backend на FastAPI для управления отзывами, жалобами и запросами клиентов медицинских филиалов.

### Core Features
- JWT-аутентификация для админ-панели.
- RBAC-авторизация: мутации (`POST /requests`) требуют прав суперпользователя.
- Аналитика по филиалу и по всем филиалам с фильтрами периода.
- Расширенная аналитика (dashboard): платформы, удовлетворённость, NPS-серии, оценки сотрудников, последние отзывы.
- Управление опубликованными отзывами (фильтры по платформе/рейтингу).
- Работа с перехваченными жалобами (список + отметка `resolved`).
- Мониторинг статусов отправленных запросов на отзыв.
- Управление настройками филиала: частота запросов, email-уведомления, специализация.
- CRUD сотрудников филиала (управление профилями площадок).
- CRUD чёрного списка клиентов (исключение из запросов на отзыв).

### Scope Boundary
- Отправка SMS/email и внешние интеграции намеренно оставлены заглушками.
- Backend хранит и отдает данные, но не выполняет реальную доставку сообщений.

---

## Technology Stack

- **Python 3.12+** - runtime.
- **FastAPI 0.115** - HTTP API и OpenAPI/Swagger.
- **SQLAlchemy 2.0** - ORM и доступ к PostgreSQL.
- **PostgreSQL 16** - основная БД.
- **Alembic** - миграции схемы.
- **Pydantic v2** + **pydantic-settings** - валидация, сериализация, конфигурация.
- **python-jose + bcrypt** - JWT и хеширование паролей.
- **Poetry** - зависимости и запуск.
- **pytest + httpx** - тестирование.
- **black, ruff, mypy** - линтинг и типизация (dev).

---

## Architecture Patterns

### Project Structure

```
medservice-backend/
├── app/
│   ├── api/v1/           # REST endpoints
│   │   ├── router.py     # Основной роутер, собирает все модули
│   │   ├── auth.py       # Аутентификация и JWT
│   │   ├── analytics.py  # Аналитика (базовая + dashboard)
│   │   ├── branches.py   # Филиалы (GET + PATCH)
│   │   ├── reviews.py    # Опубликованные отзывы
│   │   ├── complaints.py # Перехваченные жалобы
│   │   ├── requests.py   # Запросы на отзыв
│   │   ├── employees.py  # CRUD сотрудников
│   │   └── blacklist.py  # CRUD чёрного списка
│   ├── core/
│   │   ├── database.py   # SessionLocal, Base, get_db
│   │   ├── dependencies.py # get_current_user, require_superuser
│   │   └── security.py   # JWT create/decode, bcrypt hash/verify
│   ├── models/           # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── branch.py     # + настройки: timezone, emails, frequency
│   │   ├── review.py
│   │   ├── complaint.py
│   │   ├── request.py
│   │   ├── employee.py   # Сотрудники филиала
│   │   └── blacklist.py  # Чёрный список клиентов
│   ├── schemas/          # Pydantic схемы
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
│   ├── config.py         # Settings из .env (Pydantic Settings)
│   └── main.py           # FastAPI app entrypoint
├── alembic/
│   └── versions/         # Миграции
├── tests/                # pytest тесты
│   ├── conftest.py       # Фикстуры: TestClient, DB, auth
│   ├── test_auth_api.py
│   ├── test_analytics_api.py
│   ├── test_branches_api.py
│   ├── test_complaints_api.py
│   ├── test_requests_api.py
│   └── test_reviews_api.py
├── seed.py               # Заполнение тестовыми данными
├── docker-compose.yml    # PostgreSQL контейнер
└── pyproject.toml        # Poetry: зависимости, dev-инструменты
```

### API Naming Contract

- В коде Python используются `snake_case` поля (`avg_rating`, `branch_id`).
- В HTTP JSON ответы и запросы поддерживают `camelCase` (`avgRating`, `branchId`) через базовую схему `app/schemas/common.py` (`APIModel`).
- Frontend работает **без дополнительного маппинга** — сериализация/десериализация прозрачна.

---

## Authentication Flow

### Endpoints
- `POST /api/v1/auth/login` — вход по `username/password`, возвращает JWT + данные пользователя.
- `GET /api/v1/auth/me` — текущий пользователь по Bearer токену.
- `POST /api/v1/auth/forgot-password` — заглушка восстановления пароля. Всегда 200 OK (защита от перечисления).

### JWT
- Алгоритм: `HS256`.
- Время жизни: `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 мин).
- Токен ожидается в `Authorization: Bearer <token>`.
- Хеширование паролей: `bcrypt` (напрямую через библиотеку `bcrypt`, без passlib).

---

## Domain Endpoints

### Branches

- `GET /api/v1/branches`
  - Возвращает список всех филиалов.
  - Формат: `{ branches: [...], total: number }`.
  - Каждый филиал включает настройки: `timezone`, `specialization`, `requestFrequencyDays`, `complaintEmails`, `reminderEmails`.

- `PATCH /api/v1/branches/{branchId}`
  - Обновление настроек филиала (частичное).
  - Тело: `BranchUpdate` (все поля optional).
  - Возвращает: обновлённый `BranchResponse`.

### Analytics

- `GET /api/v1/analytics/{branchId}?period=week|30|90|year`
  - Базовые метрики филиала: `{ sent, reviews, complaints, avgRating }`.

- `GET /api/v1/analytics/{branchId}/dashboard?period=week|30|90|year`
  - Расширенный payload для дашборда:
  - `periodStart`, `periodEnd` — границы периода.
  - `platforms` — таблица площадок: рейтинг, отзывы, негативные.
  - `satisfaction` — распределение по звёздам (5→1).
  - `npsSmall`, `npsLarge` — NPS таймлайн (7 и 12 точек).
  - `employees` — оценки сотрудников (извлечены из текста отзывов).
  - `recentReviews` — последние отзывы.

- `GET /api/v1/analytics/branches?period=week|30|90|year`
  - Таблица по всем филиалам:
  - `{ rows: [{ id, name, requests, newReviews, interceptedComplaints, avgRating, nps }] }`.

### Reviews
- `GET /api/v1/reviews`
  - Фильтры: `branchId`, `platform`, `ratingMin`, `ratingMax`, `period`, `limit`, `offset`.
  - Возвращает: `{ reviews: [...], total }`.

### Complaints
- `GET /api/v1/complaints`
  - Фильтры: `branchId`, `resolved`, `limit`, `offset`.
  - Возвращает: `{ complaints: [...], total }`.
- `PATCH /api/v1/complaints/{complaintId}`
  - Тело: `{ resolved: boolean }`.

### Requests
- `GET /api/v1/requests`
  - Фильтры: `branchId`, `status`, `limit`, `offset`.
  - Возвращает: `{ requests: [...], total }`.
- `POST /api/v1/requests` **(требует superuser)**
  - Создает запрос на отзыв. `request_link` = UUID.
  - Реальная отправка SMS — stub.

### Employees
- `GET /api/v1/employees?branch_id={branchId}`
  - Список сотрудников филиала.
- `POST /api/v1/employees?branch_id={branchId}`
  - Создание сотрудника: `{ name, active, profiles }`.
- `PATCH /api/v1/employees/{employeeId}`
  - Частичное обновление: `{ name?, active?, profiles? }`.
- `DELETE /api/v1/employees/{employeeId}`
  - Удаление сотрудника. 204 No Content.

### Blacklist
- `GET /api/v1/blacklist?branch_id={branchId}`
  - Список клиентов в чёрном списке.
- `POST /api/v1/blacklist?branch_id={branchId}`
  - Добавление: `{ lastName, firstName, phone, reason? }`.
- `PATCH /api/v1/blacklist/{userId}`
  - Частичное обновление: `{ lastName?, firstName?, phone?, reason? }`.
- `DELETE /api/v1/blacklist/{userId}`
  - Удаление из чёрного списка. 204 No Content.

### Utility Endpoints
- `GET /` — информация о сервисе.
- `GET /health` — health check `{ status: "ok" }`.

---

## Data Model

### Main Entities

| Модель | Таблица | Описание |
|--------|---------|----------|
| `User` | `users` | Администраторы системы (username, email, bcrypt hash, is_superuser) |
| `Branch` | `branches` | Филиалы клиники с настройками |
| `Review` | `reviews` | Опубликованные отзывы. Индексы: `platform`, `published_at` |
| `Complaint` | `complaints` | Перехваченные жалобы. Индексы: `resolved`, `created_at` |
| `Request` | `requests` | Запросы клиентам. Индексы: `status`, `sent_at`. Уникальное: `request_link` |
| `Employee` | `employees` | Сотрудники филиала (name, active, profiles JSON) |
| `BlacklistUser` | `blacklist_users` | Клиенты, исключённые из запросов (фамилия, имя, телефон, причина) |

### Branch Settings Fields

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| `timezone` | `String` | `"Московское время - UTC +3"` | Часовой пояс |
| `specialization` | `String` | `"Офтальмология"` | Направление деятельности |
| `request_frequency_days` | `Integer` | `14` | Частота повторных запросов (дни) |
| `complaint_emails` | `JSON` | `[]` | Email для жалоб |
| `reminder_emails` | `JSON` | `[]` | Email для напоминаний |

### Relationships

- `Branch` → `Review`, `Complaint`, `Request`, `Employee`, `BlacklistUser` (cascade delete).
- `Employee.branch_id` → `Branch.id` (FK, indexed).
- `BlacklistUser.branch_id` → `Branch.id` (FK, indexed).

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
cp .env.example .env          # Заполнить DATABASE_URL, SECRET_KEY
poetry install
docker-compose up -d          # PostgreSQL (переменные: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
poetry run alembic upgrade head
poetry run python seed.py     # Создаёт admin + тестовые данные
poetry run python app/main.py # Запуск через uvicorn (host/port из .env)
```

### API Docs
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### First Login
- `username: admin`
- `password: 12345678`
- ⚠️ Смените пароль перед использованием в production.

### Running Tests

```bash
poetry run pytest tests/ -v
```

Тесты используют `httpx.AsyncClient` + `TestClient`, отдельную in-memory базу и фикстуры из `conftest.py`.

---

## Configuration (`app/config.py`)

Settings загружаются из `.env` через `pydantic-settings`:

| Переменная | Обязательна | Default | Описание |
|------------|-------------|---------|----------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | Ключ для JWT (изменить в prod!) |
| `DEBUG` | ❌ | `false` | Включает debug режим |
| `HOST` | ❌ | `0.0.0.0` | Хост сервера |
| `PORT` | ❌ | `8000` | Порт сервера |
| `ALGORITHM` | ❌ | `HS256` | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | TTL токена |
| `CORS_ORIGINS` | ❌ | `["http://localhost:3000"]` | JSON или строка через запятую |
| `LOG_LEVEL` | ❌ | `INFO` | Уровень логирования |
| `DATABASE_ECHO` | ❌ | `false` | Логирование SQL-запросов |

### CORS
- Принимает JSON-массив: `["http://localhost:3000"]`
- Или строку через запятую: `http://localhost:3000,https://example.com`

---

## Frontend Integration Notes

- Backend periоды: `week | 30 | 90 | year`.
- JSON-поля — `camelCase`, прозрачная замена mock API без маппингов.
- Для аналитики и фильтров используются те же query-параметры, что и во frontend типах.
- Каналы доставки (SMS/email/мессенджеры) — out of scope.
- `PATCH /branches/{id}` соответствует frontend `updateBranch()`.
- CRUD employees / blacklist соответствует настройкам и странице чёрного списка.
