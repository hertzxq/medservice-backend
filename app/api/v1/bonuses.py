"""
Admin bonus-catalog CRUD (auth required).

Manages the data the patient mini-app shows on its bonus screens:
  * branch bonuses — the clinic's own offers, scoped to a branch
  * categories + partner bonuses — the global partner catalog
  * FAQ — global

The patient mini-app reads this data (no-auth) via `GET /public/branches/{id}/mini`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_superuser,
    get_current_user,
    require_branch_access,
)
from app.models.branch import Branch
from app.models.bonus import BranchBonus, BonusCategory, PartnerBonus, FaqItem
from app.models.user import User
from app.schemas.bonus import (
    BonusAdminResponse,
    BonusCategoryCreate,
    BonusCategoryResponse,
    BonusCategoryUpdate,
    BranchBonusCreate,
    BranchBonusResponse,
    BranchBonusUpdate,
    FaqItemCreate,
    FaqItemResponse,
    FaqItemUpdate,
    PartnerBonusCreate,
    PartnerBonusResponse,
    PartnerBonusUpdate,
)

router = APIRouter(prefix="/bonuses")


def _get_or_404(db: Session, model, obj_id: int, label: str):
    obj = db.query(model).filter(model.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=label)
    return obj


def _apply(obj, payload) -> None:
    """Patch ORM `obj` with the set fields of an update schema."""
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)


# ── Aggregate (admin overview for one branch) ────────────────────────────────

@router.get("/admin", response_model=BonusAdminResponse)
async def get_bonus_admin(
    branchId: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Everything the bonus-management UI needs for one branch."""
    require_branch_access(branchId, current_user, db)

    branch_bonuses = (
        db.query(BranchBonus)
        .filter(BranchBonus.branch_id == branchId)
        .order_by(BranchBonus.sort_order, BranchBonus.id)
        .all()
    )
    categories = (
        db.query(BonusCategory)
        .order_by(BonusCategory.sort_order, BonusCategory.id)
        .all()
    )
    faq = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()

    return BonusAdminResponse(
        branch_bonuses=branch_bonuses,
        categories=categories,
        faq=faq,
    )


# ── Branch bonuses (per-branch) ──────────────────────────────────────────────

@router.get("/branch/{branch_id}", response_model=list[BranchBonusResponse])
async def list_branch_bonuses(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_branch_access(branch_id, current_user, db)
    return (
        db.query(BranchBonus)
        .filter(BranchBonus.branch_id == branch_id)
        .order_by(BranchBonus.sort_order, BranchBonus.id)
        .all()
    )


@router.post(
    "/branch/{branch_id}",
    response_model=BranchBonusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch_bonus(
    branch_id: int,
    payload: BranchBonusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_branch_access(branch_id, current_user, db)
    _get_or_404(db, Branch, branch_id, "Филиал не найден")
    bonus = BranchBonus(branch_id=branch_id, **payload.model_dump())
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    return bonus


@router.patch("/branch-items/{bonus_id}", response_model=BranchBonusResponse)
async def update_branch_bonus(
    bonus_id: int,
    payload: BranchBonusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bonus = _get_or_404(db, BranchBonus, bonus_id, "Бонус не найден")
    require_branch_access(bonus.branch_id, current_user, db)
    _apply(bonus, payload)
    db.commit()
    db.refresh(bonus)
    return bonus


@router.delete("/branch-items/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_bonus(
    bonus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bonus = _get_or_404(db, BranchBonus, bonus_id, "Бонус не найден")
    require_branch_access(bonus.branch_id, current_user, db)
    db.delete(bonus)
    db.commit()


# ── Categories (global) ──────────────────────────────────────────────────────

@router.get("/categories", response_model=list[BonusCategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return (
        db.query(BonusCategory)
        .order_by(BonusCategory.sort_order, BonusCategory.id)
        .all()
    )


@router.post(
    "/categories",
    response_model=BonusCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: BonusCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    category = BonusCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=BonusCategoryResponse)
async def update_category(
    category_id: int,
    payload: BonusCategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    category = _get_or_404(db, BonusCategory, category_id, "Категория не найдена")
    _apply(category, payload)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    category = _get_or_404(db, BonusCategory, category_id, "Категория не найдена")
    db.delete(category)  # cascades to its partner bonuses
    db.commit()


# ── Partner bonuses (global, inside a category) ──────────────────────────────

@router.post(
    "/partner-items",
    response_model=PartnerBonusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_bonus(
    payload: PartnerBonusCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    _get_or_404(db, BonusCategory, payload.category_id, "Категория не найдена")
    bonus = PartnerBonus(**payload.model_dump())
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    return bonus


@router.patch("/partner-items/{bonus_id}", response_model=PartnerBonusResponse)
async def update_partner_bonus(
    bonus_id: int,
    payload: PartnerBonusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    bonus = _get_or_404(db, PartnerBonus, bonus_id, "Бонус не найден")
    if payload.category_id is not None:
        _get_or_404(db, BonusCategory, payload.category_id, "Категория не найдена")
    _apply(bonus, payload)
    db.commit()
    db.refresh(bonus)
    return bonus


@router.delete("/partner-items/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner_bonus(
    bonus_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    bonus = _get_or_404(db, PartnerBonus, bonus_id, "Бонус не найден")
    db.delete(bonus)
    db.commit()


# ── FAQ (global) ─────────────────────────────────────────────────────────────

@router.get("/faq", response_model=list[FaqItemResponse])
async def list_faq(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()


@router.post("/faq", response_model=FaqItemResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FaqItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    item = FaqItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/faq/{faq_id}", response_model=FaqItemResponse)
async def update_faq(
    faq_id: int,
    payload: FaqItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    item = _get_or_404(db, FaqItem, faq_id, "Вопрос не найден")
    _apply(item, payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/faq/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    item = _get_or_404(db, FaqItem, faq_id, "Вопрос не найден")
    db.delete(item)
    db.commit()
