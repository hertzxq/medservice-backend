"""
Public (no-auth) endpoints consumed by the patient mini-app (medservice-mini).

Two concerns:
  * GET /public/branches/{id}/mini — branch identity + bonus/category/FAQ catalog
    for the bonus-discovery screens. Branch data is real (from the DB); the
    bonus/category/FAQ catalog is demo content synthesized per branch (there are
    no dedicated tables yet).
  * POST /public/requests/{token}/{rating|complaint|published} — drives the SMS
    review flow. `token` is the request's `request_link`. The SERVER decides
    complaint-vs-publish from the star rating (rating <= 3 → complaint).

None of these require authentication.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.models.branch import Branch
from app.models.bonus import BranchBonus, BonusCategory, FaqItem
from app.models.complaint import Complaint
from app.models.request import Request, RequestStatusEnum
from app.schemas.public import (
    BranchComplaintRequest,
    ComplaintRequest,
    ConfirmPublishedRequest,
    MiniAdminBonus,
    MiniBranch,
    MiniBranchBonus,
    MiniCategory,
    MiniFaqItem,
    MiniPlatformLink,
    MiniResponse,
    OkResponse,
    RatingRequest,
    RatingResult,
    VerificationStatus,
)

router = APIRouter(prefix="/public")

COMPLAINT_RATING_THRESHOLD = 3  # rating <= 3 → intercepted complaint (matches mini)

# Platform slug → display order; only these are surfaced to patients.
PLATFORM_SLUGS = ["yandex_maps", "google_maps", "2gis", "prodoctorov", "napopravku"]


def _iso(d: datetime) -> str:
    return d.date().isoformat()


def _date_str(d) -> str:
    """Serialize a (nullable) Date column to the ISO string the mini expects."""
    return d.isoformat() if d else ""


def _branch_platforms(branch: Branch) -> list[MiniPlatformLink]:
    """Real review-platform links for the branch, in canonical order."""
    urls = branch.platform_urls or {}
    return [
        MiniPlatformLink(platform=slug, url=urls[slug])
        for slug in PLATFORM_SLUGS
        if urls.get(slug)
    ]


def _demo_branch_bonuses(branch: Branch) -> list[MiniBranchBonus]:
    start = datetime.utcnow()
    end = start + timedelta(days=90)
    return [
        MiniBranchBonus(
            id=1, branch_id=branch.id, is_published=True, discount_percent=20,
            description="Скидка 20% на повторный приём офтальмолога в течение месяца после визита.",
            start_date=_iso(start), end_date=_iso(end), promo_code="ZRENIE20",
        ),
        MiniBranchBonus(
            id=2, branch_id=branch.id, is_published=True, discount_percent=15,
            description="−15% на комплексную диагностику зрения по предъявлению купона.",
            start_date=_iso(start), end_date=_iso(end), promo_code=None,
        ),
    ]


def _demo_categories(branch: Branch) -> list[MiniCategory]:
    start = datetime.utcnow()
    end = start + timedelta(days=120)
    city = branch.city or "Санкт-Петербург"

    def bonus(bid, cid, company, pct, desc, promo, site):
        return MiniAdminBonus(
            id=bid, category_id=cid, is_published=True, company_name=company,
            logo_url=None, city=city, discount_percent=pct, description=desc,
            start_date=_iso(start), end_date=_iso(end), promo_code=promo, website_url=site,
        )

    return [
        MiniCategory(id=1, name="Оптика и аксессуары", sort_order=1, bonuses=[
            bonus(101, 1, "Очкарик", 10, "Скидка 10% на оправы и солнцезащитные очки.", "OPT10", "https://ochkarik.ru"),
            bonus(102, 1, "Линзомат", 15, "−15% на контактные линзы и растворы.", None, "https://linzomat.ru"),
        ]),
        MiniCategory(id=2, name="Здоровье и красота", sort_order=2, bonuses=[
            bonus(201, 2, "Аптека Здоровье", 7, "Скидка 7% на витамины для глаз.", "ZDOROVIE7", "https://apteka-zdorovie.ru"),
            bonus(202, 2, "СПА-центр Релакс", 20, "−20% на программу «Отдых для глаз».", "RELAX20", "https://spa-relax.ru"),
        ]),
        MiniCategory(id=3, name="Кафе и отдых", sort_order=3, bonuses=[
            bonus(301, 3, "Кофейня Bean", 12, "Скидка 12% на кофе и десерты.", "BEAN12", "https://bean-coffee.ru"),
        ]),
    ]


def _demo_faq() -> list[MiniFaqItem]:
    return [
        MiniFaqItem(id=1, sort_order=1, question="Как воспользоваться бонусом?",
                    answer="Покажите промокод или этот экран на кассе партнёра — скидка применится автоматически."),
        MiniFaqItem(id=2, sort_order=2, question="Действует ли скидка на повторный приём?",
                    answer="Да, скидка на повторный приём действует в течение месяца после первого визита."),
        MiniFaqItem(id=3, sort_order=3, question="Можно ли совмещать несколько бонусов?",
                    answer="Бонусы клиники и партнёров не суммируются между собой, но вы можете использовать их по очереди."),
    ]


def _map_branch_bonus(b: BranchBonus) -> MiniBranchBonus:
    return MiniBranchBonus(
        id=b.id, branch_id=b.branch_id, is_published=b.is_published,
        discount_percent=b.discount_percent, description=b.description,
        start_date=_date_str(b.start_date), end_date=_date_str(b.end_date),
        promo_code=b.promo_code,
    )


def _map_partner_bonus(p) -> MiniAdminBonus:
    return MiniAdminBonus(
        id=p.id, category_id=p.category_id, is_published=p.is_published,
        company_name=p.company_name, logo_url=p.logo_url, city=p.city,
        discount_percent=p.discount_percent, description=p.description,
        start_date=_date_str(p.start_date), end_date=_date_str(p.end_date),
        promo_code=p.promo_code, website_url=p.website_url,
    )


@router.get("/branches/{branch_id}/mini", response_model=MiniResponse)
def get_branch_mini(branch_id: int, db: Session = Depends(get_db)):
    """Full payload for the patient mini-app bonus-discovery screens.

    Reads the real bonus catalog from the DB. If a part of the catalog hasn't
    been configured yet (fresh, migrated-but-unseeded install), the demo
    content stands in so the patient never sees blank screens.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    urls = branch.platform_urls or {}
    website = next((urls[s] for s in PLATFORM_SLUGS if urls.get(s)), None)

    # Clinic's own offers (per-branch).
    branch_bonuses = [
        _map_branch_bonus(b)
        for b in (
            db.query(BranchBonus)
            .filter(BranchBonus.branch_id == branch.id, BranchBonus.is_published.is_(True))
            .order_by(BranchBonus.sort_order, BranchBonus.id)
            .all()
        )
    ]

    # Global partner catalog; drop categories with no published bonuses.
    categories = []
    for c in (
        db.query(BonusCategory)
        .filter(BonusCategory.is_published.is_(True))
        .order_by(BonusCategory.sort_order, BonusCategory.id)
        .all()
    ):
        bonuses = [_map_partner_bonus(p) for p in c.bonuses if p.is_published]
        if bonuses:
            categories.append(
                MiniCategory(id=c.id, name=c.name, sort_order=c.sort_order, bonuses=bonuses)
            )

    # Global FAQ.
    faq = [
        MiniFaqItem(id=f.id, question=f.question, answer=f.answer, sort_order=f.sort_order)
        for f in (
            db.query(FaqItem)
            .filter(FaqItem.is_published.is_(True))
            .order_by(FaqItem.sort_order, FaqItem.id)
            .all()
        )
    ]

    # Demo fallback for an unconfigured catalog (per-part, independent). Gated
    # behind ALLOW_DEMO_BONUSES so production never serves fabricated offers/
    # promo codes the clinic never created (see app/config.py).
    if settings.allow_demo_bonuses:
        if not branch_bonuses:
            branch_bonuses = _demo_branch_bonuses(branch)
        if not categories:
            categories = _demo_categories(branch)
        if not faq:
            faq = _demo_faq()

    return MiniResponse(
        branch=MiniBranch(
            id=branch.id,
            public_name=branch.name,
            public_city=branch.city,
            logo_url=None,
            website_url=website,
        ),
        branch_bonuses=branch_bonuses,
        categories=categories,
        faq=faq,
    )


def _get_request_by_token(db: Session, token: str) -> Request:
    req = db.query(Request).filter(Request.request_link == token).first()
    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    return req


@router.post("/requests/{token}/opened", response_model=OkResponse)
def mark_opened(token: str, db: Session = Depends(get_db)):
    """Patient opened the review link from the SMS (the mini rating page loaded).

    Status only moves forward (sent → opened); a later re-open never downgrades
    rated/visited/published/complaint.
    """
    req = _get_request_by_token(db, token)
    if req.opened_at is None:
        req.opened_at = datetime.utcnow()
    if req.status == RequestStatusEnum.SENT:
        req.status = RequestStatusEnum.OPENED
    db.commit()
    return OkResponse(ok=True)


@router.post("/requests/{token}/visited", response_model=OkResponse)
def mark_visited(token: str, db: Session = Depends(get_db)):
    """Patient tapped a review-platform link (went to the external review site).

    Forward-only as well: never downgrades published/complaint.
    """
    req = _get_request_by_token(db, token)
    if req.status in (
        RequestStatusEnum.SENT,
        RequestStatusEnum.OPENED,
        RequestStatusEnum.RATED,
    ):
        req.status = RequestStatusEnum.VISITED
    db.commit()
    return OkResponse(ok=True)


@router.post("/requests/{token}/rating", response_model=RatingResult)
def submit_rating(token: str, payload: RatingRequest, db: Session = Depends(get_db)):
    """Record the star rating; the server picks complaint-vs-publish."""
    if not 1 <= payload.rating <= 5:
        raise HTTPException(status_code=422, detail="Оценка должна быть от 1 до 5")

    req = _get_request_by_token(db, token)
    now = datetime.utcnow()
    if req.opened_at is None:
        req.opened_at = now
    req.rated_at = now
    req.rating = payload.rating
    req.status = RequestStatusEnum.RATED

    if payload.rating <= COMPLAINT_RATING_THRESHOLD:
        outcome = "complaint"
        platforms: list[MiniPlatformLink] = []
    else:
        outcome = "publish"
        platforms = _branch_platforms(req.branch)

    db.commit()
    return RatingResult(outcome=outcome, platforms=platforms)


@router.post("/requests/{token}/complaint", response_model=OkResponse)
def submit_complaint(token: str, payload: ComplaintRequest, db: Session = Depends(get_db)):
    """Patient submitted a low-rating complaint — intercepted, never published."""
    req = _get_request_by_token(db, token)

    complaint = Complaint(
        branch_id=req.branch_id,
        client_name=req.client_name,
        client_phone=req.client_phone,
        client_email=req.client_email,
        # Реальная оценка пациента (1..3 для жалоб); fallback 2, если rating не дошёл.
        rating=req.rating or 2,
        text=payload.message.strip() or "(без комментария)",
        intercepted=True,
        resolved=False,
    )
    db.add(complaint)
    db.flush()

    req.complaint_id = complaint.id
    req.status = RequestStatusEnum.COMPLAINT
    db.commit()
    return OkResponse(ok=True)


@router.post("/branches/{branch_id}/complaint", response_model=OkResponse)
def submit_branch_complaint(
    branch_id: int, payload: BranchComplaintRequest, db: Session = Depends(get_db)
):
    """Negative feedback from the mini opened WITHOUT a request token.

    The branch link (/r/{branchId}) has no Request row to attach to, so the
    complaint lands directly on the branch — it still shows up in the clinic's
    «Отзывы и запросы → Перехваченные жалобы» feed.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    rating = payload.rating
    if rating is not None and not 1 <= rating <= 5:
        raise HTTPException(status_code=422, detail="Оценка должна быть от 1 до 5")

    complaint = Complaint(
        branch_id=branch.id,
        client_name=None,
        client_phone=None,
        client_email=None,
        # Оценка пациента (1..3 для жалоб); fallback 2, если оценки нет.
        rating=rating or 2,
        text=payload.message.strip() or "(без комментария)",
        intercepted=True,
        resolved=False,
    )
    db.add(complaint)
    db.commit()
    return OkResponse(ok=True)


@router.get("/requests/{token}/verification", response_model=VerificationStatus)
def get_verification(token: str, db: Session = Depends(get_db)):
    """Poll the verification state of a publish-claim.

    Opportunistically re-runs the matcher against already-parsed reviews, so the
    mini can flip from "проверяем" to the promo-codes screen as soon as the
    patient's review shows up on the platform (and gets parsed).
    """
    from app.services.review_match import verify_request

    req = _get_request_by_token(db, token)
    status = verify_request(db, req)
    return VerificationStatus(
        status=status,
        verified=(status == "verified"),
        verified_at=req.verified_at.isoformat() if req.verified_at else None,
    )


@router.post("/requests/{token}/published", response_model=OkResponse)
def confirm_published(
    token: str,
    payload: ConfirmPublishedRequest | None = None,
    db: Session = Depends(get_db),
):
    """Patient confirmed they left a public review (publish path).

    The patient also gives us a key to verify the review later — the name they
    used on the platform and/or the review text. The request becomes
    `pending` verification; the parse-matcher confirms it asynchronously.
    """
    req = _get_request_by_token(db, token)
    now = datetime.utcnow()
    req.status = RequestStatusEnum.PUBLISHED
    req.published_at = now

    payload = payload or ConfirmPublishedRequest()
    new_platform = (payload.platform or "").strip() or None
    new_name = (payload.reviewer_name or "").strip() or None
    new_text = (payload.review_text or "").strip() or None

    # A genuinely NEW claim (different platform/name/text) must be re-verified
    # from scratch — otherwise re-submitting a wrong name would ride the prior
    # match and the promo gate would stay open without the new claim matching
    # any real review. Only an identical re-submit is idempotent (keeps a prior
    # 'verified' so a double-POST / page remount doesn't reset it to pending).
    claim_changed = (
        new_platform != req.claimed_platform
        or new_name != req.review_claim_name
        or new_text != req.review_claim_text
    )

    req.claimed_platform = new_platform
    req.review_claim_name = new_name
    req.review_claim_text = new_text
    req.claimed_at = now

    if req.verification_status != "verified":
        req.verification_status = "pending"
    elif claim_changed:
        # Drop the stale link and re-open verification for the new claim.
        req.review_id = None
        req.verified_at = None
        req.verification_status = "pending"

    db.commit()
    return OkResponse(ok=True)
