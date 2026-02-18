"""
Review model for published customer reviews.
"""

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PlatformEnum(str, enum.Enum):
    """Enum для платформ отзывов."""

    YANDEX_MAPS = "yandex_maps"
    GOOGLE_MAPS = "google_maps"
    TWO_GIS = "2gis"
    PRODOCTOROV = "prodoctorov"
    NAPOPRAVKU = "napopravku"
    OTHER = "other"


class Review(Base):
    """
    Review model for published customer reviews.

    Attributes:
        id: Primary key
        branch_id: Foreign key к филиалу
        reviewer_name: Имя клиента (optional)
        reviewer_phone: Телефон клиента (optional)
        rating: Оценка от 1.0 до 5.0
        text: Текст отзыва (optional)
        platform: Платформа отзыва (enum)
        external_url: Ссылка на отзыв (optional)
        published_at: Дата публикации отзыва (optional)
        created_at: Timestamp создания записи
        updated_at: Timestamp последнего обновления

    Relationships:
        branch: Связь с филиалом (Branch)
    """

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    # Reviewer info
    reviewer_name = Column(String, nullable=True)
    reviewer_phone = Column(String, nullable=True)

    # Review content
    rating = Column(Float, nullable=False)  # 1.0 - 5.0
    text = Column(String, nullable=True)
    platform = Column(Enum(PlatformEnum), nullable=False)

    # External link
    external_url = Column(String, nullable=True)

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    branch = relationship("Branch", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, branch_id={self.branch_id}, rating={self.rating}, platform={self.platform})>"
