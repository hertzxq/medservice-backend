"""
Requests endpoints: get and create feedback requests.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import (
    accessible_branch_ids,
    get_current_user,
    get_current_superuser,
    require_branch_access,
)
from app.models.user import User
from app.models.branch import Branch
from app.models.blacklist import BlacklistUser
from app.models.request import Request, RequestStatusEnum
from app.schemas.request import (
    RequestsListResponse,
    RequestResponse,
    RequestCreateRequest,
    RequestCreateResponse,
    SmsResult,
    TestSmsRequest,
)
from app.services.sms import build_review_link, render_template, send_sms


def _sms_result_from_raw(raw: dict) -> SmsResult:
    """Map the sms.ru service result dict onto the API schema."""
    return SmsResult(
        ok=raw.get("ok", False),
        test=raw.get("test", False),
        sms_id=raw.get("smsId"),
        cost=raw.get("cost"),
        balance=raw.get("balance"),
        error=raw.get("error"),
    )


def _sent_this_month(db: Session, branch_id: int) -> int:
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(Request)
        .filter(Request.branch_id == branch_id, Request.sent_at >= month_start)
        .count()
    )


def _normalize_phone(phone: str | None) -> str:
    """Сравниваем телефоны по цифрам. Канонизация совпадает с sms.normalize_phone,
    чтобы чёрный список и фактическая отправка трактовали номер одинаково:
    8XXXXXXXXXX и 10-значный XXXXXXXXXX → 7XXXXXXXXXX."""
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    return digits

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

    # Multi-tenancy: accessible branch required; otherwise scope to user's branches.
    if branch_filter is not None:
        require_branch_access(branch_filter, current_user, db)
        query = query.filter(Request.branch_id == branch_filter)
    else:
        allowed = accessible_branch_ids(current_user)
        if allowed is not None:
            query = query.filter(Request.branch_id.in_(allowed))
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
            req_dict["review_url"] = req.review.external_url
        elif req.complaint:
            req_dict["rating"] = req.complaint.rating
            req_dict["platform"] = "complaint"
            
        response_requests.append(RequestResponse(**req_dict))

    return RequestsListResponse(requests=response_requests, total=total)


@router.post("", response_model=RequestCreateResponse, status_code=201)
def create_request(
    request: RequestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a feedback request and text the patient their review link.

    Clinic staff may send only for branches they have access to (the SMS goes
    out only on this explicit action — there is no scheduled mailing).
    """
    require_branch_access(request.branch_id, current_user, db)
    branch = db.query(Branch).filter(Branch.id == request.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    normalized = _normalize_phone(request.client_phone)
    if normalized:
        blacklist_entries = (
            db.query(BlacklistUser)
            .filter(BlacklistUser.branch_id == request.branch_id)
            .all()
        )
        for entry in blacklist_entries:
            if _normalize_phone(entry.phone) == normalized:
                reason = entry.reason or "без указания причины"
                raise HTTPException(
                    status_code=409,
                    detail=f"Клиент в чёрном списке филиала: {reason}",
                )

    # request_link stores the bare token; it's also the path segment the mini
    # uses (/r/{branchId}/{token}) and what /public/requests/{token} matches on.
    # Full uuid4 hex (128-bit) — this token is the ONLY authorization for the
    # unauthenticated /public/requests/{token}/* mutations, so it must be
    # unguessable. A truncated token would weaken that capability boundary.
    token = uuid.uuid4().hex
    new_request = Request(
        branch_id=request.branch_id,
        client_name=request.client_name,
        client_phone=request.client_phone,
        client_email=request.client_email,
        status=RequestStatusEnum.SENT,
        request_link=token,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Keep the SMS short: no clinicName in the URL — the mini fetches the
    # branch's name itself for the greeting.
    link = build_review_link(branch.id, token)

    # Send the review-request SMS (best-effort; failure never blocks creation).
    if not branch.sms_enabled:
        sms = SmsResult(ok=False, skipped_reason="SMS-рассылка отключена для филиала")
    else:
        limit = branch.sms_monthly_limit or 0
        if limit and _sent_this_month(db, branch.id) > limit:
            sms = SmsResult(ok=False, skipped_reason=f"Достигнут месячный лимит ({limit})")
        else:
            sms = _sms_result_from_raw(
                send_sms(new_request.client_phone, render_template(branch.sms_template, link))
            )

    response = RequestCreateResponse.model_validate(new_request)
    response.request_link = link  # return the full URL, not the bare token
    response.sms = sms
    return response


@router.post("/test-sms", response_model=SmsResult)
def send_test_sms(
    payload: TestSmsRequest,
    branch_id: int = Query(..., alias="branchId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Send a one-off test SMS for a branch (used by the mailings settings page).

    Uses a sample review link and the provided draft template (or the branch's
    saved template). Honours SMS_TEST_MODE just like real sends.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    template = payload.template if payload.template is not None else branch.sms_template
    link = build_review_link(branch.id, "test-" + uuid.uuid4().hex[:8])
    raw = send_sms(payload.phone, render_template(template, link))
    return _sms_result_from_raw(raw)


@router.post("/match-reviews")
def match_reviews(
    branch_id: int = Query(..., alias="branchId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Verify pending publish-claims against parsed reviews for a branch.

    Runs the parse-matcher on demand (it also runs automatically after each
    parse). Returns how many claims were verified and flags stale ones.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    from app.services.review_match import match_branch_reviews, mark_stale_not_found

    summary = match_branch_reviews(db, branch_id)
    summary["flagged_not_found"] = mark_stale_not_found(db, branch_id)
    return summary
