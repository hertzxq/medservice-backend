"""
Requests endpoints: get and create feedback requests.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.request import Request, RequestStatusEnum
from app.schemas.request import RequestsListResponse, RequestResponse, RequestCreateRequest, RequestCreateResponse

router = APIRouter(prefix="/requests")


@router.get("", response_model=RequestsListResponse)
async def get_requests(
    branch_id: int | None = Query(None),
    status: RequestStatusEnum | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of feedback requests with filters."""
    query = db.query(Request).options(joinedload(Request.branch))

    if branch_id:
        query = query.filter(Request.branch_id == branch_id)
    if status:
        query = query.filter(Request.status == status)

    total = query.count()
    requests = query.order_by(Request.sent_at.desc()).offset(offset).limit(limit).all()

    # Add branch name
    response_requests = []
    for req in requests:
        req_dict = RequestResponse.model_validate(req).model_dump()
        req_dict["branch_name"] = req.branch.name if req.branch else None
        response_requests.append(RequestResponse(**req_dict))

    return RequestsListResponse(requests=response_requests, total=total)


@router.post("", response_model=RequestCreateResponse, status_code=201)
async def create_request(
    request: RequestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new feedback request."""
    new_request = Request(
        branch_id=request.branch_id,
        client_name=request.client_name,
        client_phone=request.client_phone,
        client_email=request.client_email,
        status=RequestStatusEnum.SENT,
        request_link=f"https://api.medservice.com/r/stub{request.branch_id}",  # Stub link
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return RequestCreateResponse.model_validate(new_request)
