"""
Parsing endpoints: trigger review parsing and check status.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.branch import Branch
from app.parsers.runner import run_parser, detect_platform, parse_by_branch
from app.parsers.service import save_parse_result
from app.parsers.compat import run_in_playwright_loop

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parsing")

PLATFORM_LABELS = {
    "yandex_maps": "Яндекс.Карты",
    "google_maps": "Google Maps",
    "2gis": "2GIS",
    "prodoctorov": "ПроДокторов",
}

ALL_PLATFORMS = list(PLATFORM_LABELS.keys())


# ── Schemas ───────────────────────────────────────────────────────────────────

class TriggerByUrlRequest(BaseModel):
    url: str
    branch_id: int


class TriggerByBranchRequest(BaseModel):
    branch_id: int
    platforms: list[str]  # ["yandex_maps", "google_maps", "2gis", "prodoctorov"]


class TriggerResponse(BaseModel):
    status: str
    message: str


class ParsingStatusResponse(BaseModel):
    status: str  # idle | running | completed | error
    last_run_at: str | None = None
    last_result: dict | None = None
    progress: str | None = None


# ── In-memory state (simple MVP, no Redis needed) ────────────────────────────

_parsing_state: dict = {
    "status": "idle",
    "last_run_at": None,
    "last_result": None,
    "running_info": None,
    "progress": None,
}


async def _run_parse_by_url(url: str, branch_id: int, headless: bool = True) -> None:
    """Background job: parse by direct URL."""
    global _parsing_state
    _parsing_state["status"] = "running"
    _parsing_state["running_info"] = url
    _parsing_state["progress"] = "Запуск парсера..."

    try:
        result = await run_in_playwright_loop(run_parser(url, headless=headless))

        db = SessionLocal()
        try:
            summary = save_parse_result(db, result, branch_id)
        finally:
            db.close()

        _parsing_state["status"] = "completed"
        _parsing_state["last_run_at"] = datetime.utcnow().isoformat()
        # Add diagnostic hint when 0 reviews
        if summary.get("total_parsed", 0) == 0:
            summary["warning"] = (
                "Парсер не нашёл отзывов. Возможные причины: "
                "Яндекс изменил структуру страницы, или страница не загрузилась. "
                "Проверьте логи бэкенда для подробностей."
            )
        _parsing_state["last_result"] = summary
        _parsing_state["running_info"] = None
        _parsing_state["progress"] = None

    except Exception as exc:
        _parsing_state["status"] = "error"
        _parsing_state["last_run_at"] = datetime.utcnow().isoformat()
        _parsing_state["last_result"] = {"error": str(exc)}
        _parsing_state["running_info"] = None
        _parsing_state["progress"] = None
        logger.error("Ошибка парсинга по URL: %s", exc, exc_info=True)


async def _run_parse_by_branch(
    branch_name: str,
    city: str | None,
    branch_id: int,
    platforms: list[str],
    platform_urls: dict | None = None,
    headless: bool = True,
) -> None:
    """Background job: parse reviews for a branch on selected platforms.

    Uses saved platform URLs for direct parsing when available,
    falls back to search-based resolution otherwise.
    """
    global _parsing_state
    _parsing_state["status"] = "running"
    _parsing_state["running_info"] = branch_name

    saved_urls = platform_urls or {}

    all_results: dict = {
        "branch_id": branch_id,
        "branch_name": branch_name,
        "platforms_done": [],
        "platforms_failed": [],
        "total_inserted": 0,
        "total_parsed": 0,
    }

    for i, platform in enumerate(platforms, 1):
        label = PLATFORM_LABELS.get(platform, platform)
        saved_url = saved_urls.get(platform)

        try:
            if saved_url:
                # ── Fast path: direct URL parsing (no search needed) ──
                _parsing_state["progress"] = f"[{i}/{len(platforms)}] Парсим {label}..."
                logger.info("Парсинг по сохранённому URL: %s → %s", label, saved_url)

                result = await run_in_playwright_loop(
                    run_parser(saved_url, headless=headless)
                )
            else:
                # ── Slow path: search for org, then parse ──
                _parsing_state["progress"] = f"[{i}/{len(platforms)}] Ищем на {label}..."
                logger.info("Поиск и парсинг по названию: '%s' на %s", branch_name, label)

                result = await run_in_playwright_loop(
                    parse_by_branch(branch_name, city, platform, headless=headless)
                )

                # Save discovered URL for next time
                if result.source_url:
                    _save_platform_url(branch_id, platform, result.source_url)

            _parsing_state["progress"] = f"[{i}/{len(platforms)}] Сохраняем отзывы с {label}..."

            db = SessionLocal()
            try:
                summary = save_parse_result(db, result, branch_id)
            finally:
                db.close()

            all_results["platforms_done"].append({
                "platform": platform,
                "label": label,
                "parsed": summary["total_parsed"],
                "inserted": summary["inserted"],
                "skipped": summary["skipped_duplicates"],
            })
            all_results["total_inserted"] += summary["inserted"]
            all_results["total_parsed"] += summary["total_parsed"]

            logger.info("✅ %s: parsed=%d, inserted=%d", label, summary["total_parsed"], summary["inserted"])

        except Exception as exc:
            logger.error("❌ %s: %s", label, exc, exc_info=True)
            all_results["platforms_failed"].append({
                "platform": platform,
                "label": label,
                "error": str(exc),
            })

    _parsing_state["status"] = "completed"
    _parsing_state["last_run_at"] = datetime.utcnow().isoformat()
    _parsing_state["last_result"] = all_results
    _parsing_state["running_info"] = None
    _parsing_state["progress"] = None

    logger.info("Парсинг по названию завершён: %s", all_results)


def _save_platform_url(branch_id: int, platform: str, url: str) -> None:
    """Persist a discovered platform URL to the branch for future re-use."""
    try:
        db = SessionLocal()
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if branch:
            urls = dict(branch.platform_urls or {})
            urls[platform] = url
            branch.platform_urls = urls
            db.commit()
            logger.info("URL сохранён: branch=%d, %s → %s", branch_id, platform, url)
        db.close()
    except Exception as exc:
        logger.warning("Не удалось сохранить URL площадки: %s", exc)



# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/trigger", response_model=TriggerResponse)
async def trigger_parsing_by_url(
    body: TriggerByUrlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ручной запуск парсинга отзывов по прямому URL площадки.
    """
    platform = detect_platform(body.url)
    if platform == "other":
        raise HTTPException(
            status_code=422,
            detail="Не удалось определить площадку. Поддерживаются: Google Maps, Яндекс.Карты, 2GIS, ПроДокторов",
        )

    branch = db.query(Branch).filter(Branch.id == body.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    if _parsing_state["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Парсинг уже запущен: {_parsing_state['running_info']}",
        )

    background_tasks.add_task(_run_parse_by_url, body.url, body.branch_id)

    return TriggerResponse(
        status="accepted",
        message=f"Парсинг запущен для {PLATFORM_LABELS.get(platform, platform)}",
    )


@router.post("/trigger-by-branch", response_model=TriggerResponse)
async def trigger_parsing_by_branch(
    body: TriggerByBranchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Запуск парсинга отзывов по названию филиала.

    Бэкенд сам найдёт организацию на выбранных площадках
    и спарсит все отзывы.
    """
    branch = db.query(Branch).filter(Branch.id == body.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    # Validate platforms
    valid = [p for p in body.platforms if p in PLATFORM_LABELS]
    if not valid:
        raise HTTPException(
            status_code=422,
            detail="Не выбрано ни одной площадки. Доступны: " + ", ".join(PLATFORM_LABELS.values()),
        )

    if _parsing_state["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Парсинг уже запущен: {_parsing_state['running_info']}",
        )

    background_tasks.add_task(
        _run_parse_by_branch,
        branch.name,
        branch.city,
        branch.id,
        valid,
        dict(branch.platform_urls or {}),
    )

    labels = [PLATFORM_LABELS[p] for p in valid]
    return TriggerResponse(
        status="accepted",
        message=f"Поиск «{branch.name}» на {', '.join(labels)}",
    )


@router.get("/status", response_model=ParsingStatusResponse)
def get_parsing_status(
    current_user: User = Depends(get_current_user),
):
    """Статус последнего парсинга."""
    return ParsingStatusResponse(
        status=_parsing_state["status"],
        last_run_at=_parsing_state["last_run_at"],
        last_result=_parsing_state["last_result"],
        progress=_parsing_state["progress"],
    )
