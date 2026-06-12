#!/usr/bin/env python
"""
Review-verification worker.

For every branch that has *pending* publish-claims (patients who tapped
"Я оставил отзыв" and told us the name/text they used), this script:

  1. (optional, --scrape) re-parses the branch's review platforms — the actual
     "did they leave a review on the maps" check. Scraping is best-effort: it's
     slow and can be blocked/captcha'd, so a failure never blocks step 2.
  2. runs the matcher (`app/services/review_match.match_branch_reviews`) to link
     pending claims to freshly-parsed reviews and flip them to `verified`.
  3. flags claims that have been pending too long as `not_found` (admin signal
     of a likely fake — the review never appeared).

The mini polls `GET /public/requests/{token}/verification` and forwards the
patient to the promo-codes screen once their claim is `verified`.

Run manually or from cron, e.g. every 30 min.
  Local/host venv:
    */30 * * * * cd /path/to/medservice-backend && .venv/bin/python scripts/verify_reviews.py --scrape
  Dockerized prod (parsers venv + xvfb + chrome are baked into the image):
    */30 * * * * docker exec medservice_backend python scripts/verify_reviews.py --scrape

Usage:
    python scripts/verify_reviews.py [--branch N] [--scrape] [--stale-days 14]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Allow running as `python scripts/verify_reviews.py` from the backend root.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.request import Request
from app.parsers.paths import find_parsers_root
from app.parsers.service import save_parse_result
from app.services.review_match import match_branch_reviews, mark_stale_not_found

# The review parsers live in a sibling project with their OWN venv (playwright +
# browsers). We run them as subprocesses and import their JSON output — the
# backend venv has no playwright, so we never import them in-process.
# The directory may be `medservice_parsers` (prod) or `parsers` (local clone).
_REPO_ROOT = _BACKEND_ROOT.parent
PARSERS_DIR = find_parsers_root() or (_REPO_ROOT / "medservice_parsers")
PARSERS_PY = PARSERS_DIR / ".venv" / "bin" / "python"
PER_PLATFORM_TIMEOUT = 300  # seconds

# Platform slug → parser package.
PARSER_PKG = {
    "yandex_maps": "yandex_reviews",
    "google_maps": "google_reviews",
    "2gis": "twogis_reviews",
    "prodoctorov": "prodoctorov_reviews",
    "napopravku": "napopravku_reviews",
}

# Platforms that need the real Chrome channel + headful (headless gets a degraded
# page with no reviews tab). 2gis is NOT here: it uses 2GIS's public reviews API
# directly (no browser), so headless/headful is irrelevant for it.
HEADFUL_CHROME_PLATFORMS = {"google_maps"}

# On a headless Linux server there's no display for `--no-headless`, so wrap the
# headful parser in xvfb-run (a virtual X server). On macOS/dev xvfb-run is absent
# and the GUI is used directly, so the wrapper is skipped.
XVFB_RUN = shutil.which("xvfb-run")


def _branches_with_pending(db) -> list[int]:
    rows = (
        db.query(Request.branch_id)
        .filter(Request.verification_status == "pending")
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def _build_parse_result(data: dict, url: str, platform: str):
    """Convert a parser CLI's JSON output → backend ParseResult."""
    from app.parsers.models import ParseResult, ParsedReview, ParsedBusiness

    bi = data.get("business_info", {}) or {}
    reviews = [
        ParsedReview(
            author=r.get("author", "") or "",
            # Prodoctorov/napopravku rate on a float scale (e.g. 4.5) → floor to int.
            rating=int(float(r.get("rating", 5) or 5)),
            date=r.get("date", "") or "",
            text=r.get("text", "") or "",
            response=r.get("response"),
            # Prodoctorov/napopravku put the body in pros/cons; keep them so
            # save_parse_result can merge them into the review text (text-matching).
            pros=r.get("pros"),
            cons=r.get("cons"),
        )
        for r in data.get("reviews", [])
    ]
    return ParseResult(
        business_info=ParsedBusiness(
            name=bi.get("name", "") or "",
            address=bi.get("address", "") or "",
            overall_rating=bi.get("overall_rating"),
            total_reviews_on_page=bi.get("total_reviews_on_page"),
        ),
        reviews=reviews,
        total_parsed=data.get("total_parsed", len(reviews)),
        source_url=url,
        platform=platform,
    )


def _scrape_branch(branch_id: int, only_platform: str | None = None) -> int:
    """Scrape the branch's platforms via the external parsers, import results.

    Each parser runs as a subprocess in its own venv (playwright). A failure on
    one platform never blocks the others or the matcher. Returns rows inserted.
    """
    if not PARSERS_PY.exists():
        print(f"  [scrape] парсеры не найдены: {PARSERS_PY} — пропускаю скрейп")
        return 0

    db = SessionLocal()
    try:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        urls = (branch.platform_urls or {}) if branch else {}
        total = 0
        for platform, url in urls.items():
            if only_platform and platform != only_platform:
                continue
            if not url:
                continue
            pkg = PARSER_PKG.get(platform)
            if not pkg:
                continue

            tmp = Path(tempfile.gettempdir()) / f"parse_{branch_id}_{platform}.json"
            print(f"  [scrape] {platform}: {url[:64]}…")
            cmd = [str(PARSERS_PY), "-m", pkg, "--url", url, "-o", str(tmp), "--log-level", "WARNING"]
            env = os.environ.copy()
            if platform in HEADFUL_CHROME_PLATFORMS:
                # Real Chrome + headful so the site serves the full UI / no captcha.
                cmd.append("--no-headless")
                env["GOOGLE_PARSER_CHANNEL"] = "chrome"
                env["TWOGIS_PARSER_CHANNEL"] = "chrome"
                if XVFB_RUN:  # headless server → virtual display
                    cmd = [XVFB_RUN, "-a", *cmd]
            try:
                subprocess.run(
                    cmd, cwd=str(PARSERS_DIR), timeout=PER_PLATFORM_TIMEOUT,
                    check=True, capture_output=True, text=True, env=env,
                )
            except subprocess.TimeoutExpired:
                print(f"  [scrape] {platform}: таймаут ({PER_PLATFORM_TIMEOUT}s)")
                continue
            except subprocess.CalledProcessError as e:
                print(f"  [scrape] {platform}: ошибка парсера — {(e.stderr or e.stdout or '')[:140]}")
                continue

            if not tmp.exists():
                print(f"  [scrape] {platform}: парсер не создал выходной файл")
                continue

            data = json.loads(tmp.read_text(encoding="utf-8"))
            pr = _build_parse_result(data, url, platform)
            summary = save_parse_result(db, pr, branch_id)
            total += summary["inserted"]
            print(
                f"  [scrape] {platform}: распарсено {pr.total_parsed}, "
                f"добавлено {summary['inserted']}, дублей {summary['skipped_duplicates']}"
            )
        return total
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify patient review publish-claims.")
    ap.add_argument("--branch", type=int, default=None, help="Only this branch id.")
    ap.add_argument("--scrape", action="store_true", help="Re-parse platforms first (slow).")
    ap.add_argument("--platform", default=None,
                    help="With --scrape, limit to one platform (e.g. yandex_maps).")
    ap.add_argument("--stale-days", type=int, default=14, help="Flag pending older than this as not_found.")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        branch_ids = [args.branch] if args.branch else _branches_with_pending(db)
        if not branch_ids:
            print("Нет филиалов с pending-заявками. Нечего проверять.")
            return 0

        print(f"Проверяю заявки в филиалах: {branch_ids}")
        grand_verified = 0
        for bid in branch_ids:
            print(f"\n— Филиал {bid} —")
            if args.scrape:
                _scrape_branch(bid, only_platform=args.platform)
            summary = match_branch_reviews(db, bid)
            flagged = mark_stale_not_found(db, bid, older_than_days=args.stale_days)
            grand_verified += summary.get("verified", 0)
            print(
                f"  pending={summary.get('pending', 0)} "
                f"verified={summary.get('verified', 0)} "
                f"flagged_not_found={flagged}"
            )

        print(f"\nГотово. Подтверждено отзывов: {grand_verified}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
