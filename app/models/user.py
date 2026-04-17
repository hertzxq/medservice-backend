"""
User model for authentication and authorization.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    User model for admin authentication.

    Attributes:
        id: Primary key
        email: Unique email address (для восстановления пароля)
        username: Unique username (для входа)
        hashed_password: Bcrypt hashed password
        full_name: Полное имя пользователя (optional)
        phone: Номер телефона (optional)
        role: Роль в команде (optional, e.g. "Руководитель")
        is_active: Флаг активности аккаунта
        is_superuser: Флаг администратора
        created_at: Timestamp создания
        updated_at: Timestamp последнего обновления
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
