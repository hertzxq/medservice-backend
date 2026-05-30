"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""

import json
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Environments where a weak/placeholder SECRET_KEY is tolerated (local convenience).
_RELAXED_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}

# Substrings that mark a non-secret placeholder value.
_SECRET_PLACEHOLDERS = ("change_this", "replace_me", "your-secret", "changeme")

MIN_SECRET_KEY_LEN = 32


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
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    log_level: str = "INFO"

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
    def _enforce_strong_secret_in_production(self) -> "Settings":
        """Refuse to boot a non-dev environment with a weak/placeholder SECRET_KEY (C1).

        Local/dev/test keep booting with the placeholder for convenience; any other
        environment (production, staging, …) must supply a real key.
        """
        if self.environment.lower() in _RELAXED_ENVIRONMENTS:
            return self

        key = self.secret_key or ""
        lowered = key.lower()
        if len(key) < MIN_SECRET_KEY_LEN or any(
            p in lowered for p in _SECRET_PLACEHOLDERS
        ):
            raise ValueError(
                "SECRET_KEY is a placeholder or too short for "
                f"environment='{self.environment}'. Generate one with "
                "`openssl rand -hex 32` and set it via the environment."
            )

        # CORS '*' is unsafe with allow_credentials=True (credentialed
        # cross-origin reads from any site); forbid it outside dev. (L6)
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS must not contain '*' when credentials are allowed; "
                "list explicit origins instead."
            )
        return self


settings = Settings()
