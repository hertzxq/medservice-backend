"""
Branch model for clinic branches/locations.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Branch(Base):
    """
    Branch model representing a clinic location.

    Attributes:
        id: Primary key
        name: Название филиала (e.g., "Счастливый взгляд, Сенная ул. 10")
        address: Адрес филиала (optional)
        city: Город (optional)
        phone: Телефон (optional)
        timezone: Часовой пояс филиала
        specialization: Направление деятельности
        request_frequency_days: Частота отправки запросов (в днях)
        complaint_emails: Список email для перехваченных жалоб
        reminder_emails: Список email для напоминаний
        avg_rating: Средняя оценка (кэшированная метрика)
        nps_score: Net Promoter Score (кэшированная метрика)
        created_at: Timestamp создания
        updated_at: Timestamp последнего обновления

    Relationships:
        reviews: Связь с отзывами (Review)
        complaints: Связь с жалобами (Complaint)
        requests: Связь с запросами (Request)
        employees: Связь с сотрудниками (Employee)
        blacklist_users: Связь с черным списком (BlacklistUser)
    """

    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    # Настройки филиала
    timezone = Column(String, default="Московское время - UTC +3")
    specialization = Column(String, default="Офтальмология")
    request_frequency_days = Column(Integer, default=14)
    complaint_emails = Column(JSON, default=list)
    reminder_emails = Column(JSON, default=list)

    # URLs for review platforms (e.g. {"yandex_maps": "https://...", "2gis": "https://..."})
    platform_urls = Column(JSON, default=dict)

    # Кэшированные метрики для производительности
    avg_rating = Column(Float, default=0.0)
    nps_score = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    reviews = relationship("Review", back_populates="branch", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="branch", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="branch", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="branch", cascade="all, delete-orphan")
    blacklist_users = relationship("BlacklistUser", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Branch(id={self.id}, name={self.name}, city={self.city})>"
