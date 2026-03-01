"""
Requests endpoints: get and create feedback requests.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_superuser
from app.models.user import User
from app.models.branch import Branch
from app.models.request import Request, RequestStatusEnum
from app.schemas.request import RequestsListResponse, RequestResponse, RequestCreateRequest, RequestCreateResponse

router = APIRouter(prefix="/requests")


@router.get("", response_model=RequestsListResponse)
def get_requests(
    branch_id: int | None = Query(None, alias="branchId"),
    branch_id_legacy: int | None = Query(None, alias="branch_id", include_in_schema=False),
    status: RequestStatusEnum | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of feedback requests with filters."""
    branch_filter = branch_id if branch_id is not None else branch_id_legacy

    query = db.query(Request).options(
        joinedload(Request.branch),
        joinedload(Request.review),
        joinedload(Request.complaint)
    )

    if branch_filter is not None:
        query = query.filter(Request.branch_id == branch_filter)
    if status:
        query = query.filter(Request.status == status)

    total = query.count()
    requests = query.order_by(Request.sent_at.desc()).offset(offset).limit(limit).all()

    # Add branch name, rating, and platform
    response_requests = []
    for req in requests:
        req_dict = RequestResponse.model_validate(req).model_dump()
        req_dict["branch_name"] = req.branch.name if req.branch else None
        
        if req.review:
            req_dict["rating"] = req.review.rating
            req_dict["platform"] = req.review.platform.value if req.review.platform else None
        elif req.complaint:
            req_dict["rating"] = req.complaint.rating
            req_dict["platform"] = "complaint"
            
        response_requests.append(RequestResponse(**req_dict))

    return RequestsListResponse(requests=response_requests, total=total)


@router.post("", response_model=RequestCreateResponse, status_code=201)
def create_request(
    request: RequestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new feedback request."""
    branch_exists = db.query(Branch.id).filter(Branch.id == request.branch_id).first()
    if not branch_exists:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    new_request = Request(
        branch_id=request.branch_id,
        client_name=request.client_name,
        client_phone=request.client_phone,
        client_email=request.client_email,
        status=RequestStatusEnum.SENT,
        request_link=f"https://api.medservice.com/r/{uuid.uuid4().hex}",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return RequestCreateResponse.model_validate(new_request)
