"""
Platform URL detection and parser dispatch.

Detects which platform a URL belongs to and invokes the appropriate parser
from the medservice_parsers package.
"""

import re
import sys
import importlib
import logging
from pathlib import Path

from .models import ParsedReview, ParsedBusiness, ParseResult

logger = logging.getLogger(__name__)

# Add medservice_parsers to sys.path so we can import it at runtime.
_PARSERS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "medservice_parsers"
if str(_PARSERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PARSERS_ROOT))


def detect_platform(url: str) -> str:
    """Detect the review platform from a URL string.

    Returns one of: yandex_maps, google_maps, 2gis, prodoctorov, other.
    """
    url_lower = url.lower()
    # Yandex may redirect to regional TLDs: yandex.md, yandex.by, yandex.kz etc.
    if re.search(r"yandex\.\w+/maps", url_lower):
        return "yandex_maps"
    if re.search(r"google\.\w+/maps", url_lower):
        return "google_maps"
    if "2gis.ru" in url_lower or "2gis.com" in url_lower:
        return "2gis"
    if "prodoctorov.ru" in url_lower:
        return "prodoctorov"
    return "other"


async def run_parser(url: str, headless: bool = True) -> ParseResult:
    """Run the appropriate parser for *url* and return a unified ParseResult.

    Raises ValueError when the platform cannot be detected.
    """
    platform = detect_platform(url)
    logger.info("Определена площадка %s для URL: %s", platform, url)

    if platform == "google_maps":
        from google_reviews.parser import GoogleReviewsParser  # type: ignore[import-untyped]
        parser = GoogleReviewsParser(headless=headless)
        raw = await parser.parse_by_url(url)

    elif platform == "yandex_maps":
        # Force reimport to pick up changes in external parsers dir
        for mod_name in ["yandex_reviews.config", "yandex_reviews.parser"]:
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        from yandex_reviews.parser import YandexReviewsParser  # type: ignore[import-untyped]
        parser = YandexReviewsParser(headless=headless)
        raw = await parser.parse_by_url(url)

    elif platform == "2gis":
        from twogis_reviews.parser import TwoGisParser  # type: ignore[import-untyped]
        parser = TwoGisParser(headless=headless)
        raw = await parser.parse_by_url(url)

    elif platform == "prodoctorov":
        from prodoctorov_reviews.parser import ProdoctorovParser  # type: ignore[import-untyped]
        parser = ProdoctorovParser(headless=headless)
        raw = await parser.parse_by_url(url)

    else:
        raise ValueError(f"Не удалось определить площадку для URL: {url}")

    # Convert raw parser result (platform-specific pydantic) → unified ParseResult
    reviews: list[ParsedReview] = []
    for r in raw.reviews:
        data = r.model_dump()
        # Clamp rating to int 1..5 for platforms where it may be a float (prodoctorov)
        rating_raw = data.get("rating", 5)
        rating = max(1, min(5, int(round(float(rating_raw)))))
        reviews.append(ParsedReview(
            author=data.get("author", ""),
            rating=rating,
            date=data.get("date", ""),
            text=data.get("text", ""),
            response=data.get("response"),
            pros=data.get("pros"),
            cons=data.get("cons"),
        ))

    bi = raw.business_info

    if len(reviews) == 0:
        logger.warning(
            "⚠️ Парсер %s вернул 0 отзывов для URL: %s. "
            "Возможно: страница не загрузилась, селекторы устарели, "
            "или API Яндекса заблокировал запрос. "
            "Проверьте логи парсера и скриншот в _diagnostics/.",
            platform, url,
        )
    else:
        logger.info(
            "✅ Парсер %s: получено %d отзывов, бизнес: '%s'",
            platform, len(reviews), bi.name,
        )

    return ParseResult(
        business_info=ParsedBusiness(
            name=bi.name,
            address=bi.address,
            overall_rating=bi.overall_rating,
            total_reviews_on_page=bi.total_reviews_on_page,
        ),
        reviews=reviews,
        total_parsed=len(reviews),
        source_url=raw.source_url,
        platform=platform,
    )


async def parse_by_branch(
    branch_name: str,
    city: str | None,
    platform: str,
    headless: bool = True,
) -> ParseResult:
    """Search for the branch on *platform* by name, then parse its reviews.

    Raises ValueError if the org cannot be found on the platform.
    """
    from .search import resolve_org_url, build_search_query

    query = build_search_query(branch_name, city)
    logger.info("Поиск и парсинг: '%s' на %s", query, platform)

    org_url = await resolve_org_url(query, platform, headless=headless)
    if not org_url:
        raise ValueError(
            f"Не удалось найти '{branch_name}' на площадке {platform}"
        )

    logger.info("Найден URL: %s → запуск парсера", org_url)
    return await run_parser(org_url, headless=headless)

