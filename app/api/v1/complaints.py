"""
Complaints endpoints: get and update complaints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintsListResponse, ComplaintResponse, ComplaintUpdateRequest

router = APIRouter(prefix="/complaints")


@router.get("", response_model=ComplaintsListResponse)
async def get_complaints(
    branch_id: int | None = Query(None),
    resolved: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of intercepted complaints with filters."""
    query = db.query(Complaint).options(joinedload(Complaint.branch))

    if branch_id:
        query = query.filter(Complaint.branch_id == branch_id)
    if resolved is not None:
        query = query.filter(Complaint.resolved == resolved)

    total = query.count()
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()

    # Add branch name
    response_complaints = []
    for complaint in complaints:
        complaint_dict = ComplaintResponse.model_validate(complaint).model_dump()
        complaint_dict["branch_name"] = complaint.branch.name if complaint.branch else None
        response_complaints.append(ComplaintResponse(**complaint_dict))

    return ComplaintsListResponse(complaints=response_complaints, total=total)


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    request: ComplaintUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update complaint (mark as resolved)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Жалоба не найдена")

    complaint.resolved = request.resolved
    db.commit()
    db.refresh(complaint)

    complaint_dict = ComplaintResponse.model_validate(complaint).model_dump()
    complaint_dict["branch_name"] = complaint.branch.name if complaint.branch else None
    return ComplaintResponse(**complaint_dict)
