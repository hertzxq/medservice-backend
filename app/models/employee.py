"""
Employee model for clinic staff managed in settings.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Employee(Base):
    """
    Employee model representing clinic staff capable of receiving feedback.

    Attributes:
        id: Primary key
        branch_id: Ссылка на филиал
        name: ФИО сотрудника
        active: Статус активности (для переключателя запросов)
        profiles: JSON со списком ссылок на профили на площадках отзывов
    
    Relationships:
        branch: Связь с филиалом (Branch)
    """

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    profiles = Column(JSON, default=list)

    # Relationships
    branch = relationship("Branch", back_populates="employees")

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, name={self.name})>"
