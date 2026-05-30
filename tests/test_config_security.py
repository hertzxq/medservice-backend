"""Tests for fail-fast SECRET_KEY validation in config (C1)."""

import pytest
from pydantic import ValidationError

from app.config import Settings

PLACEHOLDER = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"
GOOD_KEY = "a" * 64  # 32 bytes hex-like


def _make(**overrides):
    base = dict(
        database_url="sqlite:///:memory:",
        secret_key=GOOD_KEY,
        environment="production",
    )
    base.update(overrides)
    return Settings(**base)


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        _make(secret_key=PLACEHOLDER, environment="production")


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError):
        _make(secret_key="short", environment="production")


def test_production_accepts_strong_secret():
    s = _make(secret_key=GOOD_KEY, environment="production")
    assert s.secret_key == GOOD_KEY


def test_development_allows_placeholder():
    # Local/dev must still boot with the placeholder for convenience.
    s = _make(secret_key=PLACEHOLDER, environment="development")
    assert s.secret_key == PLACEHOLDER


def test_test_environment_allows_weak_secret():
    s = _make(secret_key="test-secret-key-for-testing-only", environment="test")
    assert s.secret_key == "test-secret-key-for-testing-only"
