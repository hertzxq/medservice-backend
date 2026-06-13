"""
Verify patient publish-claims against parsed reviews.

When a patient takes the publish path they tap "Я оставил отзыв" and tell us a
key to verify it later — the name they used on the platform and/or the review
text (stored on the Request as `review_claim_name` / `review_claim_text` /
`claimed_platform`). The clinic's parser (`app/parsers/*`) scrapes real reviews
into the `reviews` table. This matcher links a *pending* request to a parsed
`Review` when they plausibly refer to the same review and flips the request to
`verified`.

Matching is heuristic — platforms don't expose per-user attribution — so we
require the same platform + a recent publish time + rating >= 4, plus a strong
content signal. Crucially, the verifying signal is the review TEXT (which a
patient who actually posted can reproduce): reviewer NAMES are public and a
name match alone is therefore insufficient (anti-forgery). See `_score`.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.review import Review

PUBLISH_MIN_RATING = 4
# A valid review is published AFTER the request was sent (the patient left it in
# response to our request) — anti-fraud: don't credit reviews that existed
# before the patient even got the request. Small skews absorb clock/timezone
# differences and platform moderation/indexing delay.
SENT_SKEW = timedelta(days=1)     # review may be timestamped a bit before sent_at
FUTURE_SKEW = timedelta(days=1)   # ...or a bit in the future vs our clock
# Fallback window when a request has no sent_at (shouldn't happen in practice).
FALLBACK_LOOKBACK = timedelta(days=60)
MATCH_THRESHOLD = 0.6  # at least one strong signal (name or text)

# ┌───────────────────────────────────────────────────────────────────────────┐
# │ TODO ВЕРНУТЬ ПЕРЕД РЕАЛЬНЫМ ЗАПУСКОМ: поставить True.                     │
# │ Антифрод «отзыв опубликован ПОСЛЕ создания запроса» временно отключён     │
# │ (2026-06-13, по просьбе заказчика) — чтобы тестировать верификацию на     │
# │ проде по уже существующим отзывам. Пока False, заявка может присвоить     │
# │ ЛЮБОЙ исторический отзыв с подходящим именем/текстом.                     │
# └───────────────────────────────────────────────────────────────────────────┘
ENFORCE_CLAIM_DATE_WINDOW = False


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def _name_tokens(s: str | None) -> set[str]:
    return {t for t in _norm(s).split() if len(t) >= 3}


def _name_matches(claim_name: str | None, fallback_name: str | None, review_name: str | None) -> bool:
    rev = _name_tokens(review_name)
    if not rev:
        return False
    claim = _name_tokens(claim_name) or _name_tokens(fallback_name)
    return bool(claim & rev)


def _text_overlap(claim_text: str | None, review_text: str | None) -> float:
    a, b = _norm(claim_text), _norm(review_text)
    if len(a) < 12 or not b:
        return 0.0
    ta, tb = set(a.split()), set(b.split())
    if not ta:
        return 0.0
    overlap = len(ta & tb) / len(ta)
    if a in b or b in a:  # patient pasted (part of) their own review
        return max(overlap, 0.9)
    return overlap


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _score(req: Request, rev: Review, claimed_at: datetime) -> float:
    if rev.rating is None or rev.rating < PUBLISH_MIN_RATING:
        return 0.0
    # Platform must match the claim (when the patient told us which one).
    if req.claimed_platform and rev.platform and rev.platform.value != req.claimed_platform:
        return 0.0
    # Time window: the review must be published after the request was sent
    # (and not in the future). A review predating the request can't be a
    # response to it — that's the anti-fraud guard.
    pub = _naive(rev.published_at)
    if ENFORCE_CLAIM_DATE_WINDOW and pub is not None:
        sent = _naive(req.sent_at)
        lower = (sent - SENT_SKEW) if sent else (claimed_at - FALLBACK_LOOKBACK)
        upper = datetime.utcnow() + FUTURE_SKEW
        if pub < lower or pub > upper:
            return 0.0
    score = 0.0
    # Name alone is a WEAK signal: reviewer names are PUBLICLY visible on the
    # platforms (Yandex/2GIS/Google), so a third party who never left a review
    # can copy any genuine reviewer's first name. A name-only claim must NOT
    # reach MATCH_THRESHOLD on its own — it only corroborates a text match.
    if _name_matches(req.review_claim_name, req.client_name, rev.reviewer_name):
        score += 0.3
    text_ov = _text_overlap(req.review_claim_text, rev.text)
    # Review TEXT is the verifying signal: a patient who pasted (part of) their
    # own review demonstrates knowledge a name-copier doesn't reliably have.
    # Continuous above the threshold so a STRONGER textual match outranks a
    # weaker one (0.5 overlap → 0.6, scaling toward 1.0 at full overlap). Strong
    # text alone still verifies — critical for platforms whose reviewer names
    # are masked (e.g. prodoctorov), where text is the only signal. Weak text
    # (0.3–0.5) only verifies when combined with a matching name (0.3 + 0.3).
    if text_ov >= 0.5:
        score += 0.6 + 0.4 * (text_ov - 0.5) / 0.5
    elif text_ov >= 0.3:
        score += 0.3
    return score


def match_branch_reviews(db: Session, branch_id: int) -> dict:
    """Verify all pending publish-claims for a branch. Returns a summary."""
    pending = (
        db.query(Request)
        .filter(
            Request.branch_id == branch_id,
            Request.verification_status == "pending",
            Request.review_id.is_(None),
        )
        .all()
    )
    if not pending:
        return {"pending": 0, "verified": 0}

    reviews = (
        db.query(Review)
        .filter(Review.branch_id == branch_id, Review.rating >= PUBLISH_MIN_RATING)
        .all()
    )

    # A parsed review belongs to at most one request.
    taken = {
        r.review_id
        for r in db.query(Request).filter(Request.review_id.isnot(None)).all()
    }

    verified = 0
    for req in pending:
        claimed_at = _naive(req.claimed_at or req.published_at) or datetime.utcnow()
        # Strictly-greater replacement (with an epsilon floor) so the FIRST
        # strongest match wins deterministically instead of the last seen.
        best, best_score = None, MATCH_THRESHOLD - 1e-9
        for rev in reviews:
            if rev.id in taken:
                continue
            s = _score(req, rev, claimed_at)
            if s > best_score:
                best, best_score = rev, s
        if best is not None:
            req.review_id = best.id
            req.verified_at = datetime.utcnow()
            req.verification_status = "verified"
            taken.add(best.id)
            verified += 1

    db.commit()
    return {"pending": len(pending), "verified": verified}


def verify_request(db: Session, req: Request) -> str:
    """Try to verify ONE pending request against already-parsed reviews.

    Cheap enough to call on every status poll from the mini. Returns the
    request's verification status ("none" if it never had a claim).
    """
    if req.verification_status != "pending" or req.review_id is not None:
        return req.verification_status or "none"

    reviews = (
        db.query(Review)
        .filter(Review.branch_id == req.branch_id, Review.rating >= PUBLISH_MIN_RATING)
        .all()
    )
    taken = {
        r.review_id
        for r in db.query(Request).filter(Request.review_id.isnot(None)).all()
    }
    claimed_at = _naive(req.claimed_at or req.published_at) or datetime.utcnow()

    best, best_score = None, MATCH_THRESHOLD - 1e-9
    for rev in reviews:
        if rev.id in taken:
            continue
        s = _score(req, rev, claimed_at)
        if s > best_score:
            best, best_score = rev, s

    if best is not None:
        req.review_id = best.id
        req.verified_at = datetime.utcnow()
        req.verification_status = "verified"
        db.commit()

    return req.verification_status or "none"


def mark_stale_not_found(db: Session, branch_id: int, older_than_days: int = 14) -> int:
    """Flag long-pending claims that never matched, for admin attention."""
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    stale = (
        db.query(Request)
        .filter(
            Request.branch_id == branch_id,
            Request.verification_status == "pending",
            Request.claimed_at.isnot(None),
            Request.claimed_at < cutoff,
        )
        .all()
    )
    for req in stale:
        req.verification_status = "not_found"
    db.commit()
    return len(stale)
