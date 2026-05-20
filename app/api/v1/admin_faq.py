"""Admin FAQ CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_superuser
from app.models.faq import FaqItem
from app.models.user import User
from app.schemas.faq import FaqItemCreate, FaqItemResponse, FaqItemUpdate


router = APIRouter(prefix="/admin/faq")


def _get_or_404(db: Session, item_id: int) -> FaqItem:
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Вопрос не найден"
        )
    return item


@router.get("", response_model=list[FaqItemResponse])
async def list_faq(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Список вопросов/ответов, отсортированный по sort_order."""
    items = db.query(FaqItem).order_by(FaqItem.sort_order, FaqItem.id).all()
    return [FaqItemResponse.model_validate(i) for i in items]


@router.post("", response_model=FaqItemResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FaqItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Создать запись FAQ."""
    item = FaqItem(
        question=payload.question,
        answer=payload.answer,
        sort_order=payload.sort_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return FaqItemResponse.model_validate(item)


@router.patch("/{item_id}", response_model=FaqItemResponse)
async def update_faq(
    item_id: int,
    payload: FaqItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Обновить запись FAQ."""
    item = _get_or_404(db, item_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return FaqItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Удалить запись FAQ."""
    item = _get_or_404(db, item_id)
    db.delete(item)
    db.commit()
