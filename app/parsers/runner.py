"""
Platform URL detection and parser dispatch.

Detects which platform a URL belongs to and invokes the appropriate parser
from the medservice_parsers package.
"""

import re
import sys
import ipaddress
import importlib
import logging
from pathlib import Path
from urllib.parse import urlparse

from .models import ParsedReview, ParsedBusiness, ParseResult

logger = logging.getLogger(__name__)

# Allowed schemes for any URL we hand to a headless browser.
_ALLOWED_SCHEMES = {"http", "https"}

# Exact registrable domains for platforms without regional TLDs. A host matches
# when it equals the domain or is a subdomain of it.
_EXACT_DOMAIN_PLATFORMS = (
    ("2gis.ru", "2gis"),
    ("2gis.com", "2gis"),
    ("prodoctorov.ru", "prodoctorov"),
    ("napopravku.ru", "napopravku"),
)

# Maps platforms use regional TLDs (yandex.by, google.com.tr, …) and require /maps.
_YANDEX_HOST_RE = re.compile(r"(?:.+\.)?yandex\.[a-z]{2,}$")
_GOOGLE_HOST_RE = re.compile(r"(?:.+\.)?google\.[a-z.]{2,}$")


def _host_matches(host: str, domain: str) -> bool:
    """True when *host* is exactly *domain* or a subdomain of it."""
    return host == domain or host.endswith("." + domain)


def _host_is_ip_literal(host: str) -> bool:
    """True when *host* is a raw IP literal (we only ever allow named domains)."""
    candidate = host.strip("[]")  # IPv6 in URLs is bracketed
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False

# Add medservice_parsers to sys.path so we can import it at runtime.
_PARSERS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "medservice_parsers"
if str(_PARSERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PARSERS_ROOT))


def detect_platform(url: str) -> str:
    """Detect the review platform from a URL string (SSRF-hardened, H3).

    Matches on the parsed *hostname* (not a substring), requires an http/https
    scheme, and rejects raw-IP hosts. This prevents smuggling an internal or
    cloud-metadata target past the allow-list while still containing a platform
    keyword, e.g. http://169.254.169.254/maps?x=yandex.ru or
    file:///etc/passwd#prodoctorov.ru.

    Returns one of: yandex_maps, google_maps, 2gis, prodoctorov, napopravku, other.
    """
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return "other"

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return "other"

    host = (parsed.hostname or "").lower()
    if not host or _host_is_ip_literal(host):
        return "other"

    path = parsed.path.lower()

    # Maps platforms: regional TLDs + a /maps path segment.
    if _YANDEX_HOST_RE.match(host) and "/maps" in path:
        return "yandex_maps"
    if _GOOGLE_HOST_RE.match(host) and "/maps" in path:
        return "google_maps"

    for domain, platform in _EXACT_DOMAIN_PLATFORMS:
        if _host_matches(host, domain):
            return platform

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

    elif platform == "napopravku":
        from napopravku_reviews.parser import NapopravkuReviewsParser  # type: ignore[import-untyped]
        parser = NapopravkuReviewsParser(headless=headless)
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

