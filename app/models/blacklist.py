"""
BlacklistUser model for users excluded from review requests.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class BlacklistUser(Base):
    """
    BlacklistUser model representing clients that should not receive review requests.

    Attributes:
        id: Primary key
        branch_id: Ссылка на филиал
        last_name: Фамилия
        first_name: Имя
        phone: Телефонный номер
        reason: Причина добавления в черный список
    
    Relationships:
        branch: Связь с филиалом (Branch)
    """

    __tablename__ = "blacklist_users"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    reason = Column(String, nullable=True)

    # Relationships
    branch = relationship("Branch", back_populates="blacklist_users")

    def __repr__(self) -> str:
        return f"<BlacklistUser(id={self.id}, name={self.last_name} {self.first_name})>"
