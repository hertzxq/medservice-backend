"""
Complaint model for intercepted customer complaints.
"""

from sqlalchemy import CheckConstraint, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Complaint(Base):
    """
    Complaint model for intercepted negative feedback.

    Attributes:
        id: Primary key
        branch_id: Foreign key к филиалу
        client_name: Имя клиента (optional)
        client_phone: Телефон клиента (optional)
        client_email: Email клиента (optional)
        rating: Целочисленная оценка (2..5)
        text: Текст жалобы
        intercepted: Флаг перехвата (true = не опубликовано)
        resolved: Флаг решения проблемы
        created_at: Timestamp создания
        updated_at: Timestamp последнего обновления

    Relationships:
        branch: Связь с филиалом (Branch)
    """

    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("rating IN (2, 3, 4, 5)", name="ck_complaints_rating_allowed_values"),
    )

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    # Client info
    client_name = Column(String, nullable=True)
    client_phone = Column(String, nullable=True)
    client_email = Column(String, nullable=True)

    # Complaint content
    rating = Column(Integer, nullable=False)  # 2 - 5
    text = Column(String, nullable=False)

    # Status
    intercepted = Column(Boolean, default=True)  # Перехвачено до публикации
    resolved = Column(Boolean, default=False, index=True)  # Проблема решена

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    branch = relationship("Branch", back_populates="complaints")

    def __repr__(self) -> str:
        return f"<Complaint(id={self.id}, branch_id={self.branch_id}, rating={self.rating}, resolved={self.resolved})>"
