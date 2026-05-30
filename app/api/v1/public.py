"""Public (no-auth) endpoints for the patient mini-app."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.branch import Branch
from app.models.bonus import BonusCategory, BranchBonus
from app.models.complaint import Complaint
from app.models.faq import FaqItem
from app.models.request import Request, RequestStatusEnum
from app.schemas.bonus import AdminBonusResponse, BranchBonusResponse
from app.schemas.common import APIModel
from app.schemas.faq import FaqItemResponse
from app.schemas.request import (
    MiniComplaintRequest,
    MiniComplaintResponse,
    MiniPlatformLink,
    MiniRatingRequest,
    MiniRatingResponse,
)

# Ratings at or below this are intercepted as complaints, never published (domain rule).
COMPLAINT_RATING_MAX = 3


router = APIRouter(prefix="/public")


class _MiniBranch(APIModel):
    id: int
    public_name: str | None = None
    public_city: str | None = None
    logo_url: str | None = None
    website_url: str | None = None


class _MiniCategory(APIModel):
    id: int
    name: str
    sort_order: int
    bonuses: list[AdminBonusResponse]


class MiniResponse(APIModel):
    branch: _MiniBranch
    branch_bonuses: list[BranchBonusResponse]
    categories: list[_MiniCategory]
    faq: list[FaqItemResponse]


def _bonus_is_active(
    start: datetime.date, end: datetime.date, today: datetime.date
) -> bool:
    return start <= today <= end


@router.get("/branches/{branch_id}/mini", response_model=MiniResponse)
async def get_branch_mini(branch_id: int, db: Session = Depends(get_db)):
    """Public payload for the mini-app: branch branding + active published bonuses + FAQ."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch or not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Филиал не найден"
        )

    today = datetime.date.today()

    branch_bonuses = [
        b
        for b in (
            db.query(BranchBonus)
            .filter(BranchBonus.branch_id == branch_id, BranchBonus.is_published)
            .order_by(BranchBonus.id.desc())
            .all()
        )
        if _bonus_is_active(b.start_date, b.end_date, today)
    ]

    categories: list[_MiniCategory] = []
    cats = (
        db.query(BonusCategory)
        .order_by(BonusCategory.sort_order, BonusCategory.id)
        .all()
    )
    for cat in cats:
        active = [
            b
            for b in cat.bonuses
            if b.is_published and _bonus_is_active(b.start_date, b.end_date, today)
        ]
        if not active:
            continue
        categories.append(
            _MiniCategory(
                id=cat.id,
                name=cat.name,
                sort_order=cat.sort_order,
                bonuses=[AdminBonusResponse.model_validate(b) for b in active],
            )
        )

    faq = [
        FaqItemResponse.model_validate(item)
        for item in db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    ]

    return MiniResponse(
        branch=_MiniBranch.model_validate(branch),
        branch_bonuses=[BranchBonusResponse.model_validate(b) for b in branch_bonuses],
        categories=categories,
        faq=faq,
    )


def _get_request_by_token(db: Session, token: str) -> Request:
    req = db.query(Request).filter(Request.public_token == token).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Запрос не найден"
        )
    return req


@router.post("/requests/{token}/rating", response_model=MiniRatingResponse)
async def submit_rating(
    token: str, body: MiniRatingRequest, db: Session = Depends(get_db)
):
    """Patient submits a star rating. The SERVER decides complaint-vs-publish (H4).

    rating <= 3 → 'complaint' (no platform links returned; patient is routed to the
    director form). rating > 3 → 'publish' with the branch's real platform URLs.
    """
    req = _get_request_by_token(db, token)

    req.rating = body.rating
    req.rated_at = datetime.datetime.now(datetime.timezone.utc)
    if req.status in (RequestStatusEnum.SENT, RequestStatusEnum.OPENED):
        req.status = RequestStatusEnum.RATED

    if body.rating <= COMPLAINT_RATING_MAX:
        db.commit()
        return MiniRatingResponse(outcome="complaint", platforms=[])

    branch = db.query(Branch).filter(Branch.id == req.branch_id).first()
    urls = (branch.platform_urls or {}) if branch else {}
    platforms = [
        MiniPlatformLink(platform=key, url=value)
        for key, value in urls.items()
        if value
    ]
    db.commit()
    return MiniRatingResponse(outcome="publish", platforms=platforms)


@router.post(
    "/requests/{token}/complaint",
    response_model=MiniComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_complaint(
    token: str, body: MiniComplaintRequest, db: Session = Depends(get_db)
):
    """Persist a low-rating complaint and intercept it (never published)."""
    req = _get_request_by_token(db, token)

    if req.rating is None or req.rating > COMPLAINT_RATING_MAX:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Жалобу можно отправить только при оценке 3 и ниже",
        )

    complaint = Complaint(
        branch_id=req.branch_id,
        client_name=req.client_name,
        client_phone=req.client_phone,
        client_email=req.client_email,
        rating=req.rating,
        text=body.message,
        intercepted=True,
        resolved=False,
    )
    db.add(complaint)
    db.flush()

    req.complaint_id = complaint.id
    req.status = RequestStatusEnum.COMPLAINT
    db.commit()
    return MiniComplaintResponse(ok=True)


@router.post("/requests/{token}/published", response_model=MiniComplaintResponse)
async def confirm_published(token: str, db: Session = Depends(get_db)):
    """Patient confirms they left a public review (publish path only)."""
    req = _get_request_by_token(db, token)

    if req.rating is not None and req.rating <= COMPLAINT_RATING_MAX:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Низкая оценка не публикуется",
        )

    req.status = RequestStatusEnum.PUBLISHED
    req.published_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return MiniComplaintResponse(ok=True)
