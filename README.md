# MedService Backend API

REST API для управления отзывами медицинских клиник.

## Технологии

- FastAPI 0.115
- PostgreSQL + SQLAlchemy
- JWT Authentication
- Alembic migrations
- Poetry dependency management

## Быстрый старт

```bash
# 1. Установка зависимостей
poetry install

# 2. Запуск PostgreSQL
docker-compose up -d

# 3. Применить миграции
poetry run alembic upgrade head

# 4. Заполнить тестовыми данными
poetry run python seed.py

# 5. Запустить сервер
poetry run uvicorn app.main:app --reload
```

## Документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Тестовые данные

- **Username:** admin
- **Password:** password123
