"""Bonus-related models: per-branch bonuses and admin global catalog."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BranchBonus(Base):
    """Bonus created by a clinic for its own patients."""

    __tablename__ = "branch_bonuses"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(
        Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
    )
    is_published = Column(Boolean, nullable=False, default=True)
    discount_percent = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    branch = relationship("Branch", back_populates="bonuses")


class BonusCategory(Base):
    """Top-level grouping in the admin catalog."""

    __tablename__ = "bonus_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bonuses = relationship(
        "AdminBonus",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="AdminBonus.id",
    )


class AdminBonus(Base):
    """Bonus inside an admin catalog category (third-party partner)."""

    __tablename__ = "admin_bonuses"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("bonus_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_published = Column(Boolean, nullable=False, default=True)
    company_name = Column(String, nullable=False)
    logo_url = Column(Text, nullable=True)
    city = Column(String, nullable=False)
    discount_percent = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("BonusCategory", back_populates="bonuses")
