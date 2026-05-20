"""Public (no-auth) endpoints for the patient mini-app."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.branch import Branch
from app.models.bonus import BonusCategory, BranchBonus
from app.models.faq import FaqItem
from app.schemas.bonus import AdminBonusResponse, BranchBonusResponse
from app.schemas.common import APIModel
from app.schemas.faq import FaqItemResponse


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
