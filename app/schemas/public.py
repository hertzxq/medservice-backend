"""
Pydantic schemas for the public (no-auth) mini-app API.

These mirror the shapes consumed by `medservice-mini` (see its
`src/types/mini.ts`). All fields are serialized in camelCase via the
shared `APIModel` alias generator.
"""

from app.schemas.common import APIModel


# ── GET /public/branches/{id}/mini ───────────────────────────────────────────

class MiniBranch(APIModel):
    id: int
    public_name: str | None
    public_city: str | None
    logo_url: str | None
    website_url: str | None


class MiniBranchBonus(APIModel):
    id: int
    branch_id: int
    is_published: bool
    discount_percent: int
    description: str
    start_date: str
    end_date: str
    promo_code: str | None


class MiniAdminBonus(APIModel):
    id: int
    category_id: int
    is_published: bool
    company_name: str
    logo_url: str | None
    city: str
    discount_percent: int
    description: str
    start_date: str
    end_date: str
    promo_code: str | None
    website_url: str | None


class MiniCategory(APIModel):
    id: int
    name: str
    sort_order: int
    bonuses: list[MiniAdminBonus]


class MiniFaqItem(APIModel):
    id: int
    question: str
    answer: str
    sort_order: int


class MiniResponse(APIModel):
    branch: MiniBranch
    branch_bonuses: list[MiniBranchBonus]
    categories: list[MiniCategory]
    faq: list[MiniFaqItem]


# ── POST /public/requests/{token}/... ────────────────────────────────────────

class RatingRequest(APIModel):
    rating: int


class MiniPlatformLink(APIModel):
    platform: str
    url: str


class RatingResult(APIModel):
    outcome: str  # "complaint" | "publish"
    platforms: list[MiniPlatformLink]


class ComplaintRequest(APIModel):
    message: str


class BranchComplaintRequest(APIModel):
    """Complaint sent from the mini opened WITHOUT an SMS request token."""
    message: str
    rating: int | None = None


class ConfirmPublishedRequest(APIModel):
    """Patient's claim that they left a public review, with a key to verify it."""
    platform: str | None = None
    reviewer_name: str | None = None
    review_text: str | None = None


class OkResponse(APIModel):
    ok: bool


class VerificationStatus(APIModel):
    """Polled by the mini to gate the promo-codes screen on a confirmed review."""
    status: str  # none | pending | verified | not_found
    verified: bool
    verified_at: str | None = None
