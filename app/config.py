"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""

import json
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Known placeholder secrets that must never be used in production. The app
# refuses to start in production if SECRET_KEY matches one of these (or is too
# short), preventing token forgery via a well-known default key.
_PLACEHOLDER_SECRETS = {
    "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32",
    "changeme",
    "change_me",
    "secret",
    "secret_key",
    "your-secret-key",
    "test-secret-key",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "MedService Feedback API"
    debug: bool = False
    environment: str = "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str
    database_echo: bool = False

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"

    # SMS (sms.ru)
    sms_ru_api_id: str | None = None
    sms_test_mode: bool = True
    sms_sender: str | None = None
    mini_public_url: str = "http://localhost:5173"

    # When True, the patient mini falls back to fabricated demo bonuses/FAQ for
    # branches with no published catalog. MUST stay False in production so real
    # patients never see invented offers/promo codes the clinic won't honor.
    allow_demo_bonuses: bool = False

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """Allow both JSON array and comma-separated CORS_ORIGINS."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []

            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass

            return [origin.strip() for origin in raw.split(",") if origin.strip()]

        return value

    @model_validator(mode="after")
    def _enforce_production_hardening(self):
        """Refuse to boot a production deployment with an insecure config.

        In production a weak/placeholder SECRET_KEY would let anyone forge a
        valid JWT for any user (incl. superuser), so we fail fast. Dev/test
        environments are exempt so local runs and the test suite keep working.
        """
        if self.environment == "production":
            lowered = self.secret_key.lower()
            looks_like_placeholder = any(
                marker in lowered for marker in ("replace", "change", "example", "your-")
            )
            if (
                self.secret_key in _PLACEHOLDER_SECRETS
                or looks_like_placeholder
                or len(self.secret_key) < 32
            ):
                raise ValueError(
                    "SECRET_KEY looks like a placeholder or is shorter than 32 chars; "
                    "set a strong random value in production (e.g. `openssl rand -hex 32`)."
                )
            if self.debug:
                raise ValueError("DEBUG must be False in production.")
        return self


settings = Settings()
