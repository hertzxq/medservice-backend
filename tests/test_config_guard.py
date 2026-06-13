"""
Tests for the production hardening guard in app.config.Settings.
"""

import pytest
from pydantic import ValidationError

from app.config import Settings

_DB = "postgresql://u:p@db:5432/x"
_STRONG = "a" * 40  # 40 chars, not a placeholder


def _make(**over):
    base = dict(database_url=_DB, secret_key=_STRONG, environment="production", debug=False)
    base.update(over)
    return Settings(**base)


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        _make(secret_key="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32")


def test_production_rejects_replace_me_secret():
    # The example file's value is 35 chars and must still be rejected.
    with pytest.raises(ValidationError):
        _make(secret_key="REPLACE_ME_WITH_OPENSSL_RAND_HEX_32")


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError):
        _make(secret_key="short")


def test_production_rejects_debug_true():
    with pytest.raises(ValidationError):
        _make(debug=True)


def test_production_accepts_strong_secret():
    s = _make()
    assert s.environment == "production"
    assert s.secret_key == _STRONG


def test_non_production_allows_weak_secret():
    # Dev/test are exempt so local runs and the test suite keep working.
    s = _make(environment="development", secret_key="test-secret-key", debug=True)
    assert s.environment == "development"


def test_claim_date_window_enforced_by_default():
    # Антифрод верификации отзывов не должен быть выключен «из коробки»:
    # ослабление допустимо только явной строкой в .env (см. review_match.py).
    s = _make()
    assert s.enforce_claim_date_window is True
