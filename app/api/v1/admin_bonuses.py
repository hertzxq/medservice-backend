"""Admin-only endpoints: bonus catalog (categories + admin bonuses)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_superuser
from app.models.bonus import AdminBonus, BonusCategory
from app.models.user import User
from app.schemas.bonus import (
    AdminBonusBase,
    AdminBonusCreate,
    AdminBonusResponse,
    AdminBonusUpdate,
    BonusCategoryCreate,
    BonusCategoryResponse,
    BonusCategoryUpdate,
)

router = APIRouter(prefix="/admin/bonus-categories")


def _get_category_or_404(db: Session, category_id: int) -> BonusCategory:
    cat = db.query(BonusCategory).filter(BonusCategory.id == category_id).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена"
        )
    return cat


def _get_admin_bonus_or_404(
    db: Session, category_id: int, bonus_id: int
) -> AdminBonus:
    bonus = (
        db.query(AdminBonus)
        .filter(AdminBonus.id == bonus_id, AdminBonus.category_id == category_id)
        .first()
    )
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бонус не найден"
        )
    return bonus


@router.get("", response_model=list[BonusCategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Список всех категорий с вложенными бонусами."""
    cats = (
        db.query(BonusCategory)
        .order_by(BonusCategory.sort_order, BonusCategory.id)
        .all()
    )
    return [BonusCategoryResponse.model_validate(c) for c in cats]


@router.post(
    "",
    response_model=BonusCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: BonusCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Создать новую категорию."""
    if db.query(BonusCategory).filter(BonusCategory.name == payload.name).first():
        raise HTTPException(
            status_code=400,
            detail="Категория с таким именем уже существует",
        )
    cat = BonusCategory(name=payload.name, sort_order=payload.sort_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return BonusCategoryResponse.model_validate(cat)


@router.patch("/{category_id}", response_model=BonusCategoryResponse)
async def update_category(
    category_id: int,
    payload: BonusCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Обновить категорию (имя / порядок)."""
    cat = _get_category_or_404(db, category_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return BonusCategoryResponse.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Удалить категорию (каскадно вместе с её бонусами)."""
    cat = _get_category_or_404(db, category_id)
    db.delete(cat)
    db.commit()


@router.post(
    "/{category_id}/bonuses",
    response_model=AdminBonusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_bonus(
    category_id: int,
    payload: AdminBonusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Создать бонус внутри категории."""
    _get_category_or_404(db, category_id)
    bonus = AdminBonus(category_id=category_id, **payload.model_dump())
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    return AdminBonusResponse.model_validate(bonus)


@router.patch(
    "/{category_id}/bonuses/{bonus_id}",
    response_model=AdminBonusResponse,
)
async def update_admin_bonus(
    category_id: int,
    bonus_id: int,
    payload: AdminBonusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Обновить бонус (любые поля + isPublished)."""
    bonus = _get_admin_bonus_or_404(db, category_id, bonus_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(bonus, key, value)

    try:
        AdminBonusBase.model_validate(
            {
                "companyName": bonus.company_name,
                "logoUrl": bonus.logo_url,
                "city": bonus.city,
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
    return AdminBonusResponse.model_validate(bonus)


@router.delete(
    "/{category_id}/bonuses/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_admin_bonus(
    category_id: int,
    bonus_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Удалить бонус из категории."""
    bonus = _get_admin_bonus_or_404(db, category_id, bonus_id)
    db.delete(bonus)
    db.commit()
