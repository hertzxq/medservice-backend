"""
Seed script: полностью сбрасывает данные домена и создаёт двух пользователей.

⚠️  ДЕСТРУКТИВНО. Скрипт удаляет все строки из таблиц requests, complaints,
    reviews, employees, blacklist_users, branches и users. Используйте только
    в dev/staging. Реальные данные (в т.ч. результаты парсинга) будут потеряны.

Итог:
  - user  / 12345678  (is_superuser=False)  — вход в дашборд на /login
  - admin / 12345678  (is_superuser=True)   — вход в админку на /admin/login
"""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.blacklist import BlacklistUser
from app.models.branch import Branch
from app.models.complaint import Complaint
from app.models.employee import Employee
from app.models.request import Request
from app.models.review import Review
from app.models.user import User


DEFAULT_PASSWORD = "12345678"


def seed_database() -> None:
    db: Session = SessionLocal()

    try:
        print("[cleanup] Очистка таблиц домена...")
        # Порядок важен: дети → родители (FK).
        for model in (Request, Complaint, Review, Employee, BlacklistUser, Branch, User):
            deleted = db.query(model).delete()
            print(f"  - {model.__tablename__}: удалено {deleted}")
        db.commit()

        print("[seed] Создание пользователей...")
        hashed = get_password_hash(DEFAULT_PASSWORD)
        db.add_all(
            [
                User(
                    email="user@medservice.com",
                    username="user",
                    hashed_password=hashed,
                    full_name="Пользователь сервиса",
                    is_active=True,
                    is_superuser=False,
                ),
                User(
                    email="admin@medservice.com",
                    username="admin",
                    hashed_password=hashed,
                    full_name="Администратор",
                    is_active=True,
                    is_superuser=True,
                ),
            ]
        )
        db.commit()

        print("\n[done] Сид-учётки:")
        print(f"   Dashboard   : user  / {DEFAULT_PASSWORD}  (is_superuser=False)")
        print(f"   Admin panel : admin / {DEFAULT_PASSWORD}  (is_superuser=True)")
        print("[warn] Смените пароли перед production.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
