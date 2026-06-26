"""
Unisender integration for transactional account emails.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

UNISENDER_SEND_EMAIL_URL = "https://api.unisender.com/ru/api/sendEmail"


def _render_password_reset_body(reset_link: str) -> str:
    return f"""
<p>Вы запросили восстановление пароля в MedService.</p>
<p><a href="{reset_link}">Задайте новый пароль</a></p>
<p>Если вы не запрашивали восстановление, просто проигнорируйте это письмо.</p>
""".strip()


def send_password_reset_email(*, to_email: str, reset_link: str) -> dict:
    """
    Send a password reset email via Unisender. Never raises.

    Returns a result dict with at least `{ok, error}`.
    """
    if not settings.unisender_api_key:
        return {"ok": False, "error": "UNISENDER_API_KEY не задан"}
    if not settings.unisender_sender_email:
        return {"ok": False, "error": "UNISENDER_SENDER_EMAIL не задан"}
    if not settings.unisender_list_id:
        return {"ok": False, "error": "UNISENDER_LIST_ID не задан"}

    payload = {
        "format": "json",
        "api_key": settings.unisender_api_key,
        "email": to_email,
        "sender_name": settings.unisender_sender_name,
        "sender_email": settings.unisender_sender_email,
        "subject": "Восстановление пароля",
        "body": _render_password_reset_body(reset_link),
        "list_id": settings.unisender_list_id,
    }

    try:
        response = httpx.post(UNISENDER_SEND_EMAIL_URL, data=payload, timeout=15.0)
        data = response.json()
    except Exception as exc:
        logger.warning("Unisender password reset email failed: %s", exc)
        return {"ok": False, "error": f"Сбой обращения к Unisender: {exc}"}

    if "error" in data:
        error = data.get("error") or f"Unisender code={data.get('code')}"
        logger.warning("Unisender password reset email not OK: %s", error)
        return {"ok": False, "error": error, "raw": data}

    return {"ok": True, "raw": data}
