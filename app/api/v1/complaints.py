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
def get_complaints(
    branch_id: int | None = Query(None, alias="branchId"),
    branch_id_legacy: int | None = Query(None, alias="branch_id", include_in_schema=False),
    resolved: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of intercepted complaints with filters."""
    branch_filter = branch_id if branch_id is not None else branch_id_legacy

    query = db.query(Complaint).options(joinedload(Complaint.branch))

    if branch_filter is not None:
        query = query.filter(Complaint.branch_id == branch_filter)
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
def update_complaint(
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
