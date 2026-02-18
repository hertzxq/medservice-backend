"""
Request model for feedback request tracking.
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RequestStatusEnum(str, enum.Enum):
    """Enum для статусов запросов."""

    SENT = "sent"  # Запрос отправлен
    OPENED = "opened"  # Открыл ссылку
    RATED = "rated"  # Поставил оценку
    VISITED = "visited"  # Перешел на платформу отзывов
    PUBLISHED = "published"  # Отзыв опубликован
    COMPLAINT = "complaint"  # Жалоба


class Request(Base):
    """
    Request model for tracking feedback requests sent to clients.

    Attributes:
        id: Primary key
        branch_id: Foreign key к филиалу
        client_name: Имя клиента
        client_phone: Телефон клиента
        client_email: Email клиента (optional)
        status: Текущий статус запроса (enum)
        request_link: Уникальная ссылка для трекинга (optional)
        review_id: Связь с итоговым отзывом (optional)
        complaint_id: Связь с итоговой жалобой (optional)
        sent_at: Timestamp отправки запроса
        opened_at: Timestamp открытия ссылки (optional)
        rated_at: Timestamp оценки (optional)
        published_at: Timestamp публикации (optional)
        created_at: Timestamp создания записи
        updated_at: Timestamp последнего обновления

    Relationships:
        branch: Связь с филиалом (Branch)
    """

    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    # Client info
    client_name = Column(String, nullable=False)
    client_phone = Column(String, nullable=False)
    client_email = Column(String, nullable=True)

    # Request tracking
    status = Column(Enum(RequestStatusEnum), default=RequestStatusEnum.SENT, nullable=False)
    request_link = Column(String, nullable=True)  # Уникальная ссылка для трекинга

    # Связь с результатом
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)

    # Timestamps
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    opened_at = Column(DateTime(timezone=True), nullable=True)
    rated_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    branch = relationship("Branch", back_populates="requests")

    def __repr__(self) -> str:
        return f"<Request(id={self.id}, branch_id={self.branch_id}, status={self.status})>"
