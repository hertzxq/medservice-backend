"""User-facing bonus endpoints: branch branding + branch bonuses."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.branch import Branch
from app.models.bonus import BranchBonus
from app.models.user import User
from app.schemas.bonus import (
    BrandingResponse,
    BrandingUpdate,
    BranchBonusBase,
    BranchBonusCreate,
    BranchBonusResponse,
    BranchBonusUpdate,
)

router = APIRouter(prefix="/branches/{branch_id}")


def _get_branch_or_404(db: Session, branch_id: int) -> Branch:
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Филиал не найден")
    return branch


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить публичную брендовую шапку филиала."""
    branch = _get_branch_or_404(db, branch_id)
    return BrandingResponse.model_validate(branch)


@router.patch("/branding", response_model=BrandingResponse)
async def update_branding(
    branch_id: int,
    payload: BrandingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить публичную брендовую шапку филиала."""
    branch = _get_branch_or_404(db, branch_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(branch, key, value)
    db.commit()
    db.refresh(branch)
    return BrandingResponse.model_validate(branch)


@router.get("/bonuses", response_model=list[BranchBonusResponse])
async def list_branch_bonuses(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список бонусов филиала."""
    _get_branch_or_404(db, branch_id)
    items = (
        db.query(BranchBonus)
        .filter(BranchBonus.branch_id == branch_id)
        .order_by(BranchBonus.id.desc())
        .all()
    )
    return [BranchBonusResponse.model_validate(b) for b in items]


@router.post(
    "/bonuses",
    response_model=BranchBonusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch_bonus(
    branch_id: int,
    payload: BranchBonusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать бонус для филиала."""
    _get_branch_or_404(db, branch_id)
    bonus = BranchBonus(branch_id=branch_id, **payload.model_dump())
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    return BranchBonusResponse.model_validate(bonus)


@router.patch("/bonuses/{bonus_id}", response_model=BranchBonusResponse)
async def update_branch_bonus(
    branch_id: int,
    bonus_id: int,
    payload: BranchBonusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a branch bonus (any subset of fields, including isPublished)."""
    bonus = (
        db.query(BranchBonus)
        .filter(BranchBonus.id == bonus_id, BranchBonus.branch_id == branch_id)
        .first()
    )
    if not bonus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бонус не найден")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(bonus, key, value)

    # Re-validate cross-field invariant (end_date >= start_date) via Pydantic,
    # so the 422 envelope matches the CREATE endpoint.
    try:
        BranchBonusBase.model_validate(
            {
                "discountPercent": bonus.discount_percent,
                "description": bonus.description,
                "startDate": bonus.start_date,
                "endDate": bonus.end_date,
                "isPublished": bonus.is_published,
            }
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    db.commit()
    db.refresh(bonus)
    return BranchBonusResponse.model_validate(bonus)


@router.delete("/bonuses/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_bonus(
    branch_id: int,
    bonus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить бонус филиала."""
    bonus = (
        db.query(BranchBonus)
        .filter(BranchBonus.id == bonus_id, BranchBonus.branch_id == branch_id)
        .first()
    )
    if not bonus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бонус не найден")
    db.delete(bonus)
    db.commit()
