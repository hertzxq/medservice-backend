"""Pydantic schemas for bonuses (branding, branch bonuses, admin catalog)."""

import datetime

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel


MAX_LOGO_BASE64_LEN = 200 * 1024  # ~150 KB binary


def _validate_logo(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not value.startswith("data:image/png;base64,"):
        raise ValueError("logoUrl must be a data:image/png;base64,... string")
    if len(value) > MAX_LOGO_BASE64_LEN:
        raise ValueError("logoUrl exceeds 200 KB")
    return value


def _non_empty(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field} must not be empty")
    return stripped


# --- Branding ---------------------------------------------------------------


class BrandingResponse(APIModel):
    public_name: str | None = None
    public_city: str | None = None
    logo_url: str | None = None
    website_url: str | None = None


class BrandingUpdate(APIModel):
    public_name: str | None = None
    public_city: str | None = None
    logo_url: str | None = None
    website_url: str | None = None

    @field_validator("logo_url")
    @classmethod
    def _check_logo(cls, v: str | None) -> str | None:
        return _validate_logo(v)


# --- Branch bonus -----------------------------------------------------------


class BranchBonusBase(APIModel):
    discount_percent: int = Field(ge=1, le=100)
    description: str
    start_date: datetime.date
    end_date: datetime.date
    is_published: bool = True
    promo_code: str | None = None

    @field_validator("description")
    @classmethod
    def _check_description(cls, v: str) -> str:
        out = _non_empty(v, field="description")
        assert out is not None
        return out

    @model_validator(mode="after")
    def _check_dates(self) -> "BranchBonusBase":
        if self.end_date < self.start_date:
            raise ValueError("endDate must be on or after startDate")
        return self


class BranchBonusCreate(BranchBonusBase):
    pass


class BranchBonusUpdate(APIModel):
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    description: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    is_published: bool | None = None
    promo_code: str | None = None

    @field_validator("description")
    @classmethod
    def _check_description(cls, v: str | None) -> str | None:
        return _non_empty(v, field="description")


class BranchBonusResponse(APIModel):
    id: int
    branch_id: int
    is_published: bool
    discount_percent: int
    description: str
    start_date: datetime.date
    end_date: datetime.date
    promo_code: str | None = None


# --- Bonus category ---------------------------------------------------------


class BonusCategoryCreate(APIModel):
    name: str
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        out = _non_empty(v, field="name")
        assert out is not None
        return out


class BonusCategoryUpdate(APIModel):
    name: str | None = None
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str | None) -> str | None:
        return _non_empty(v, field="name")


# --- Admin bonus ------------------------------------------------------------


class AdminBonusBase(APIModel):
    company_name: str
    logo_url: str | None = None
    city: str
    discount_percent: int = Field(ge=1, le=100)
    description: str
    start_date: datetime.date
    end_date: datetime.date
    is_published: bool = True
    promo_code: str | None = None
    website_url: str | None = None

    @field_validator("company_name")
    @classmethod
    def _check_company(cls, v: str) -> str:
        out = _non_empty(v, field="companyName")
        assert out is not None
        return out

    @field_validator("city")
    @classmethod
    def _check_city(cls, v: str) -> str:
        out = _non_empty(v, field="city")
        assert out is not None
        return out

    @field_validator("description")
    @classmethod
    def _check_description(cls, v: str) -> str:
        out = _non_empty(v, field="description")
        assert out is not None
        return out

    @field_validator("logo_url")
    @classmethod
    def _check_logo(cls, v: str | None) -> str | None:
        return _validate_logo(v)

    @model_validator(mode="after")
    def _check_dates(self) -> "AdminBonusBase":
        if self.end_date < self.start_date:
            raise ValueError("endDate must be on or after startDate")
        return self


class AdminBonusCreate(AdminBonusBase):
    pass


class AdminBonusUpdate(APIModel):
    company_name: str | None = None
    logo_url: str | None = None
    city: str | None = None
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    description: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    is_published: bool | None = None
    promo_code: str | None = None
    website_url: str | None = None

    @field_validator("company_name")
    @classmethod
    def _check_company(cls, v: str | None) -> str | None:
        return _non_empty(v, field="companyName")

    @field_validator("city")
    @classmethod
    def _check_city(cls, v: str | None) -> str | None:
        return _non_empty(v, field="city")

    @field_validator("description")
    @classmethod
    def _check_description(cls, v: str | None) -> str | None:
        return _non_empty(v, field="description")

    @field_validator("logo_url")
    @classmethod
    def _check_logo(cls, v: str | None) -> str | None:
        return _validate_logo(v)


class AdminBonusResponse(APIModel):
    id: int
    category_id: int
    is_published: bool
    company_name: str
    logo_url: str | None
    city: str
    discount_percent: int
    description: str
    start_date: datetime.date
    end_date: datetime.date
    promo_code: str | None = None
    website_url: str | None = None


class BonusCategoryResponse(APIModel):
    id: int
    name: str
    sort_order: int
    bonuses: list[AdminBonusResponse]
