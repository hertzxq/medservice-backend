"""
Search resolver — finds the direct URL of an organization on review platforms
by searching for its name + address using Playwright.

Flow: search query → open platform search page → find org → return direct URL.
"""

import re
import logging
from urllib.parse import quote_plus

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


def build_search_query(branch_name: str, city: str | None = None) -> str:
    """Build a search query string from a branch name and optional city."""
    parts = [branch_name]
    if city:
        parts.append(city)
    return " ".join(parts)


async def resolve_org_url(
    query: str,
    platform: str,
    headless: bool = True,
) -> str | None:
    """Search for an organization on the given platform and return its direct
    page URL. Returns *None* when the organisation cannot be found.

    Supported platforms: google_maps, yandex_maps, 2gis, prodoctorov, napopravku.
    """
    logger.info("Поиск организации на %s: %s", platform, query)

    if platform == "google_maps":
        return await _resolve_google(query, headless)
    elif platform == "yandex_maps":
        return await _resolve_yandex(query, headless)
    elif platform == "2gis":
        return await _resolve_2gis(query, headless)
    elif platform == "prodoctorov":
        return await _resolve_prodoctorov(query, headless)
    elif platform == "napopravku":
        return await _resolve_napopravku(query, headless)
    else:
        logger.warning("Неизвестная площадка для поиска: %s", platform)
        return None


# ── Google Maps ───────────────────────────────────────────────────────────────

async def _resolve_google(query: str, headless: bool) -> str | None:
    """Google Maps: search → if single place found, return its URL."""
    search_url = f"https://www.google.com/maps/search/{quote_plus(query)}"
    logger.debug("Google search URL: %s", search_url)

    # For Google Maps, a specific search usually resolves directly to the place.
    # The URL changes to /maps/place/... — which the parser can handle.
    # So we just return the search URL and let the Google parser navigate.
    return search_url


# ── Yandex Maps ───────────────────────────────────────────────────────────────

async def _resolve_yandex(query: str, headless: bool) -> str | None:
    """Yandex Maps: search → click first result → return org URL."""
    search_url = f"https://yandex.ru/maps/?text={quote_plus(query)}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent=USER_AGENT,
        )
        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(5000)

            # Check if we landed directly on an org page
            current_url = page.url
            if "/org/" in current_url:
                logger.info("Yandex: прямое попадание на орг: %s", current_url)
                return current_url

            # Try clicking the first search result — multiple selector strategies
            clicked = await page.evaluate("""() => {
                // Strategy 1: links to /org/ pages
                const orgLinks = document.querySelectorAll('a[href*="/org/"]');
                for (const link of orgLinks) {
                    if (link.offsetWidth > 0 && link.offsetHeight > 0) {
                        link.click();
                        return 'org_link';
                    }
                }
                // Strategy 2: search result cards (class-based)
                const cards = document.querySelectorAll(
                    '.search-snippet-view, .search-business-snippet-view, ' +
                    '[class*="SearchSnippet"], [class*="searchItem"]'
                );
                for (const card of cards) {
                    const link = card.querySelector('a');
                    if (link && link.offsetWidth > 0) {
                        link.click();
                        return 'card_link';
                    }
                }
                // Strategy 3: any visible link in the sidebar that looks like an org
                const sidebar = document.querySelector('.scroll__container, [class*="sidebar"], [class*="panel"]');
                if (sidebar) {
                    const links = sidebar.querySelectorAll('a');
                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        if (href.includes('/org/') && link.offsetWidth > 0) {
                            link.click();
                            return 'sidebar_link';
                        }
                    }
                }
                return null;
            }""")

            if clicked:
                logger.debug("Yandex: кликнули по результату (%s)", clicked)
                await page.wait_for_timeout(3000)
                current_url = page.url
                if "/org/" in current_url:
                    logger.info("Yandex: найдена организация: %s", current_url)
                    return current_url

            # Last resort: check URL again
            current_url = page.url
            if "/org/" in current_url:
                return current_url

            logger.warning("Yandex: организация не найдена для запроса: %s", query)
            return None

        except Exception as exc:
            logger.error("Yandex search error: %s", exc)
            return None
        finally:
            await browser.close()


# ── 2GIS ──────────────────────────────────────────────────────────────────────

async def _resolve_2gis(query: str, headless: bool) -> str | None:
    """2GIS: search → click first result → return firm URL."""
    search_url = f"https://2gis.ru/search/{quote_plus(query)}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent=USER_AGENT,
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(4000)

            # Click the first search result card
            clicked = await page.evaluate("""() => {
                // 2GIS: look for links to /firm/ pages
                const links = document.querySelectorAll('a[href*="/firm/"]');
                for (const link of links) {
                    if (link.offsetWidth > 0 && link.offsetHeight > 0) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }""")

            if clicked:
                await page.wait_for_timeout(3000)

            # Check URL for /firm/ pattern
            current_url = page.url
            if "/firm/" in current_url:
                # Remove /tab/ if present, we'll let the parser add /tab/reviews
                base_url = re.sub(r"/tab/.*$", "", current_url)
                logger.info("2GIS: найдена организация: %s", base_url)
                return base_url

            logger.warning("2GIS: организация не найдена для запроса: %s", query)
            return None

        except Exception as exc:
            logger.error("2GIS search error: %s", exc)
            return None
        finally:
            await browser.close()


# ── ПроДокторов ───────────────────────────────────────────────────────────────

async def _resolve_prodoctorov(query: str, headless: bool) -> str | None:
    """Prodoctorov: search → click first clinic result → return URL."""
    search_url = f"https://prodoctorov.ru/search/?q={quote_plus(query)}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent=USER_AGENT,
        )
        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # Click the first clinic/lpu link in search results
            clicked = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href*="/lpu/"]');
                for (const link of links) {
                    if (link.offsetWidth > 0) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }""")

            if clicked:
                await page.wait_for_timeout(2000)

            current_url = page.url
            if "/lpu/" in current_url:
                logger.info("Prodoctorov: найдена клиника: %s", current_url)
                return current_url

            logger.warning("Prodoctorov: клиника не найдена для запроса: %s", query)
            return None

        except Exception as exc:
            logger.error("Prodoctorov search error: %s", exc)
            return None
        finally:
            await browser.close()


# ── НаПоправку ────────────────────────────────────────────────────────────────

# Город по умолчанию — субдомен `{city}.napopravku.ru`. Для клиник не из СПб
# используйте прямой URL в Branch.platform_urls['napopravku'] — минуя resolve.
_NAPOPRAVKU_DEFAULT_CITY = "spb"

_NAPOPRAVKU_SEARCH_INPUT_SELECTORS = [
    "input[placeholder*='Врач']",
    "input[placeholder*='клиника']",
    "input[type='search']",
    "input[type='text'][id*='dropdown']",
]

_NAPOPRAVKU_CLINIC_BASE_RE = re.compile(r"^(https?://[^/]+/clinics/[a-z0-9-]+/)", re.IGNORECASE)


async def _resolve_napopravku(query: str, headless: bool) -> str | None:
    """Napopravku: ввод в главный searchbox -> Enter -> URL клиники.

    Использует тот же путь, что и живой пользователь: открываем главную
    `{city}.napopravku.ru/`, печатаем запрос, жмём Enter — сайт сам
    редиректит на страницу клиники. Это надёжнее парсинга suggest-списка:
    его разметка меняется и может вернуть не-клинику.

    Возвращает базовый URL клиники (без /otzyvy/) — парсер добавит суффикс
    автоматически в `NapopravkuReviewsParser.parse_by_url`.
    """
    main_url = f"https://{_NAPOPRAVKU_DEFAULT_CITY}.napopravku.ru/"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent=USER_AGENT,
        )
        page = await context.new_page()

        try:
            await page.goto(main_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)

            search_input = None
            for sel in _NAPOPRAVKU_SEARCH_INPUT_SELECTORS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        search_input = el
                        break
                except Exception:
                    continue

            if not search_input:
                logger.warning("Napopravku: поле поиска не найдено на главной")
                return None

            await search_input.click()
            await page.wait_for_timeout(300)
            await search_input.fill("")
            await search_input.type(query, delay=50)
            await page.wait_for_timeout(2500)

            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3500)

            current_url = page.url
            match = _NAPOPRAVKU_CLINIC_BASE_RE.match(current_url)
            if match:
                base = match.group(1)
                logger.info("Napopravku: найдена клиника -> %s", base)
                return base

            logger.warning(
                "Napopravku: клиника не найдена для '%s' (конечный URL: %s)",
                query, current_url,
            )
            return None

        except Exception as exc:
            logger.error("Napopravku search error: %s", exc)
            return None
        finally:
            await browser.close()
