"""
Pydantic schemas for admin bonus-catalog CRUD.

Responses serialize in camelCase via the shared `APIModel` alias generator,
matching the admin frontend (`lib/api/bonuses.ts`). Dates are plain `date`
(ISO `YYYY-MM-DD` on the wire). The patient mini-app reads a different,
string-dated shape — see `app/schemas/public.py`.
"""

from datetime import date

from app.schemas.common import APIModel


# ── Branch bonuses (clinic's own, per-branch) ────────────────────────────────

class BranchBonusBase(APIModel):
    is_published: bool = True
    discount_percent: int = 0
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    promo_code: str | None = None
    sort_order: int = 0


class BranchBonusCreate(BranchBonusBase):
    pass


class BranchBonusUpdate(APIModel):
    is_published: bool | None = None
    discount_percent: int | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    promo_code: str | None = None
    sort_order: int | None = None


class BranchBonusResponse(BranchBonusBase):
    id: int
    branch_id: int


# ── Partner bonuses (global, inside a category) ──────────────────────────────

class PartnerBonusBase(APIModel):
    is_published: bool = True
    company_name: str
    logo_url: str | None = None
    city: str = ""
    discount_percent: int = 0
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    promo_code: str | None = None
    website_url: str | None = None
    sort_order: int = 0


class PartnerBonusCreate(PartnerBonusBase):
    category_id: int


class PartnerBonusUpdate(APIModel):
    category_id: int | None = None
    is_published: bool | None = None
    company_name: str | None = None
    logo_url: str | None = None
    city: str | None = None
    discount_percent: int | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    promo_code: str | None = None
    website_url: str | None = None
    sort_order: int | None = None


class PartnerBonusResponse(PartnerBonusBase):
    id: int
    category_id: int


# ── Categories (global) ──────────────────────────────────────────────────────

class BonusCategoryBase(APIModel):
    name: str
    sort_order: int = 0
    is_published: bool = True


class BonusCategoryCreate(BonusCategoryBase):
    pass


class BonusCategoryUpdate(APIModel):
    name: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None


class BonusCategoryResponse(BonusCategoryBase):
    id: int
    bonuses: list[PartnerBonusResponse] = []


# ── FAQ (global) ─────────────────────────────────────────────────────────────

class FaqItemBase(APIModel):
    question: str
    answer: str
    sort_order: int = 0
    is_published: bool = True


class FaqItemCreate(FaqItemBase):
    pass


class FaqItemUpdate(APIModel):
    question: str | None = None
    answer: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None


class FaqItemResponse(FaqItemBase):
    id: int


# ── Aggregate (admin overview for one branch) ────────────────────────────────

class BonusAdminResponse(APIModel):
    branch_bonuses: list[BranchBonusResponse]
    categories: list[BonusCategoryResponse]
    faq: list[FaqItemResponse]
