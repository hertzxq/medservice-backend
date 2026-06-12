"""
sms.ru integration — sending review-request SMS.

Test mode (settings.sms_test_mode / SMS_TEST_MODE=True) asks sms.ru to validate
the number and route WITHOUT delivering a real message or spending balance.
Flip SMS_TEST_MODE=False to go live (requires balance and, for a custom sender
name, an approved `from` in the sms.ru cabinet).
"""

import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SMS_RU_SEND_URL = "https://sms.ru/sms/send"

DEFAULT_TEMPLATE = "Оцените визит: {link}"


def normalize_phone(phone: str | None) -> str | None:
    """Normalize an RU phone to sms.ru's 11-digit `7XXXXXXXXXX` form, or None."""
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    if len(digits) == 11 and digits[0] == "7":
        return digits
    return None


def build_review_link(branch_id: int, token: str, clinic_name: str | None = None) -> str:
    """Public mini-app URL the patient opens from the SMS.

    When ``clinic_name`` is given it's passed as ``?clinicName=`` so the rating
    screen greets the patient with the real branch name instead of the default.
    """
    base = settings.mini_public_url.rstrip("/")
    url = f"{base}/r/{branch_id}/{token}"
    if clinic_name:
        url += f"?clinicName={quote(clinic_name)}"
    return url


def render_template(template: str | None, link: str) -> str:
    """Substitute the `{link}` placeholder in a branch SMS template."""
    return (template or DEFAULT_TEMPLATE).replace("{link}", link)


def send_sms(to: str, msg: str, *, test: bool | None = None) -> dict:
    """
    Send a single SMS via sms.ru. Never raises — returns a result dict:
        {ok, test, to, smsId, statusCode, cost, balance, error}
    """
    api_id = settings.sms_ru_api_id
    if not api_id:
        return {"ok": False, "error": "SMS_RU_API_ID не задан", "test": True}

    phone = normalize_phone(to)
    if not phone:
        return {"ok": False, "error": f"Некорректный номер телефона: {to!r}"}

    use_test = settings.sms_test_mode if test is None else test
    params: dict[str, object] = {"api_id": api_id, "to": phone, "msg": msg, "json": 1}
    if use_test:
        params["test"] = 1
    if settings.sms_sender:
        params["from"] = settings.sms_sender

    try:
        resp = httpx.get(SMS_RU_SEND_URL, params=params, timeout=15.0)
        data = resp.json()
    except Exception as exc:  # network / JSON errors must not break request creation
        logger.warning("sms.ru request failed: %s", exc)
        return {"ok": False, "error": f"Сбой обращения к sms.ru: {exc}", "test": use_test}

    sms_block = (data.get("sms") or {}).get(phone, {})
    ok = data.get("status") == "OK" and sms_block.get("status") == "OK"
    result = {
        "ok": ok,
        "test": use_test,
        "to": phone,
        "smsId": sms_block.get("sms_id"),
        "statusCode": sms_block.get("status_code") or data.get("status_code"),
        "cost": sms_block.get("cost"),
        "balance": data.get("balance"),
        "error": None
        if ok
        else (
            sms_block.get("status_text")
            or data.get("status_text")
            or f"sms.ru status_code={sms_block.get('status_code') or data.get('status_code')}"
        ),
    }
    if not ok:
        logger.warning("sms.ru send not OK: %s", result["error"])
    return result
