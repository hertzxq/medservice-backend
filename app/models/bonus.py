"""
Bonus catalog models for the patient mini-app.

Three concerns, mirroring the shapes consumed by `medservice-mini`
(see its `src/types/mini.ts`) and the public schemas in `app/schemas/public.py`:

  * BranchBonus  — the clinic's OWN offers, scoped to a single branch
                   ("Индивидуальные предложения" on the mini brand page).
  * BonusCategory + PartnerBonus — the GLOBAL partner catalog grouped by
                   category (e.g. "Оптика", "Здоровье и красота").
  * FaqItem      — the GLOBAL FAQ shown at the bottom of the bonus screens.

Categories/partner bonuses/FAQ are global (not branch-scoped): a partner deal
is offered to all clinics, with its own `city` field. Only the clinic's own
`BranchBonus` rows carry a `branch_id`.
"""

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BranchBonus(Base):
    """A clinic's own offer, shown only for its branch."""

    __tablename__ = "branch_bonuses"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    is_published = Column(Boolean, default=True, nullable=False)
    discount_percent = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=False, default="")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    promo_code = Column(String, nullable=True)

    sort_order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    branch = relationship("Branch", back_populates="branch_bonuses")

    def __repr__(self) -> str:
        return f"<BranchBonus(id={self.id}, branch_id={self.branch_id}, -{self.discount_percent}%)>"


class BonusCategory(Base):
    """A global partner category (e.g. "Оптика и аксессуары")."""

    __tablename__ = "bonus_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bonuses = relationship(
        "PartnerBonus",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="PartnerBonus.sort_order",
    )

    def __repr__(self) -> str:
        return f"<BonusCategory(id={self.id}, name={self.name})>"


class PartnerBonus(Base):
    """A global partner offer inside a category."""

    __tablename__ = "partner_bonuses"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer, ForeignKey("bonus_categories.id"), nullable=False, index=True
    )

    is_published = Column(Boolean, default=True, nullable=False)
    company_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    city = Column(String, nullable=False, default="")
    discount_percent = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=False, default="")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    promo_code = Column(String, nullable=True)
    website_url = Column(String, nullable=True)

    sort_order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("BonusCategory", back_populates="bonuses")

    def __repr__(self) -> str:
        return f"<PartnerBonus(id={self.id}, company={self.company_name})>"


class FaqItem(Base):
    """A global FAQ entry shown on the bonus screens."""

    __tablename__ = "faq_items"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<FaqItem(id={self.id}, q={self.question[:24]!r})>"
