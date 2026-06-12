# Аудит Backend API (medservice-backend)

По результатам анализа кодовой базы (FastAPI, SQLAlchemy, Pydantic) составлен список проблем и точек роста, разделенный по приоритету.

---

## 🔴 Критические проблемы (P0 - Исправить немедленно)

### 1. Утечка секретов в репозиторий
Файл `.env` закоммичен в репозиторий и содержит реальные пароли и секреты:
```env
SECRET_KEY=CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32
DATABASE_URL=postgresql://medservice_user:securepassword123@localhost:5432/medservice_db
```
**Решение:** 
- Добавить `.env` в `.gitignore`.
- Переименовать текущий `.env` в `.env.example` (с фейковыми данными).
- Сгенерировать новый `SECRET_KEY` (например, через `openssl rand -hex 32`) на сервере.
- Сменить пароль к БД в production.

### 2. Утечка пароля в логах (seed.py)
Скрипт `seed.py` выводит пароль администратора в системный stdout:
```python
print(f"👤 Login credentials: username=admin, password={default_password}")
```
**Решение:** Убрать логирование паролей открытым текстом.

### 3. Использование Deprecated API (`datetime.utcnow`)
Во многих файлах (например, `analytics.py`, `reviews.py`, `security.py`, `seed.py`) используется устаревший метод:
```python
# ❌ Deprecated в Python 3.12
expire = datetime.utcnow() + timedelta(...)
```
**Решение:** Заменить на `datetime.now(timezone.utc)`.

### 4. Использование Deprecated API (`declarative_base`)
В `app/core/database.py`:
```python
# ❌ Legacy
from sqlalchemy.ext.declarative import declarative_base 
Base = declarative_base()
```
**Решение:**
```python
# ✅ Modern
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
```

---

## 🟡 Архитектурные проблемы и рефакторинг (P1 - Ближайшие задачи)

### 1. Отсутствие сервисного слоя (Бизнес-логика в роутах)
Сейчас весь код (парсинг ответов, SQL запросы, агрегация) находится прямо в эндпоинтах. Особенно критично это для `app/api/v1/analytics.py` (файл на **538 строк**).
**Решение:** 
Создать директорию `app/services/` и вынести логику работы с БД туда (например, `AnalyticsService`, `BranchService`).

### 2. Copy-paste паттерн для обогащения данных (`branch_name`)
В эндпоинтах `reviews.py`, `complaints.py`, `requests.py` повторяется один и тот же цикл:
```python
for item in items:
    item_dict = ItemResponse.model_validate(item).model_dump()
    item_dict["branch_name"] = item.branch.name if item.branch else None
    response.append(ItemResponse(**item_dict))
```
**Решение:** Использовать возможности Pydantic (`@computed_field`, `from_attributes=True`) или подтягивать `branch.name` сразу на уровне SQL-запроса через JOIN, чтобы маппинг происходил автоматически.

### 3. Загрузка всех данных в память (Проблемы производительности)
В `branches.py` эндпоинт `/branches` вытягивает все записи из БД:
```python
branches = db.query(Branch).all()
```
В дашборде `analytics.py` мы тоже грузим все отзывы в Python для агрегации метрик.
**Решение:** 
- Для списков внедрить пагинацию (`limit`, `offset`).
- Для аналитики использовать SQL-агрегации (GROUP BY) вместо обработки списков в Python.

### 4. Неконсистентность `async def` и `def`
Часть эндпоинтов объявлена как `async def` (auth), а часть как `def` (analytics). 
Поскольку под капотом используется синхронный SQLAlchemy (`Session`), FastAPI будет запускать `async def` эндпоинты в `threadpool` с лишним overhead.
**Решение:** Либо перевести весь проект на асинхронную алхимию (`AsyncSession`, `asyncpg`), либо сделать все роуты обычными `def`.

### 5. Отсутствует Rate Limiting и Refresh Токены
- Нет лимитов на `/auth/login`, что делает возможным перебор паролей (bruteforce).
- Жизнь токена — всего 60 минут, механизма обновления (Refresh Token) нет — пользователя будет постоянно разлогинивать.

---

## ⚪ Прочие улучшения (P2 - Технический долг)

1. **Связь User и Branch:** Модель `User` никак не привязана к филиалу. Авторизованный пользователь получает доступ к аналитике **всех** филиалов. Для реального продукта (Role-Based Access Control) нужна привязка менеджеров к их филиалам.
2. **Очистка Legacy параметров:** В роутерах до сих пор висят `alias="branch_id"` и `include_in_schema=False`. Когда фронтенд окончательно переедет на camelCase, эти костыли нужно удалить.
3. **Единый формат ошибок (i18n):** Сейчас ответы об ошибках идут в разнобой: `"Branch not found"` (англ) и `"Жалоба не найдена"` (рус). Надо выбрать что-то одно.
4. **Тесты (сейчас их всего 15):**
   - Отсутствуют unit-тесты для Pydantic схем и методов.
   - 0 тестов на эндпоинты управления сотрудниками (`employees.py`).
   - 0 тестов на эндпоинты черного списка (`blacklist.py`).
   - `conftest.py` пересоздает базу на каждый тест, что может замедлить тестирование в будущем.
5. **Фальшивый Health-check:** Эндпоинт `/health` просто возвращает `{"status": "ok"}`, даже если база данных лежит. Надо добавить `db.execute(text("SELECT 1"))` для реальной проверки живости.
