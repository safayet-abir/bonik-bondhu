"""Application settings from environment variables (TRD §6)."""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str = "postgresql+psycopg://bb:bb@localhost:5432/bonik_bondhu"
    # Used only by pytest; the test suite drops and recreates this database's schema.
    TEST_DATABASE_URL: str = ""
    SECRET_SALT: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    OWNER_SESSION_DAYS: int = 7  # SUG-03
    LENDER_SESSION_HOURS: int = 8  # SUG-03
    # DEC-22 + SUG-47: primary provider; the other configured one is the fallback for text features
    LLM_PROVIDER: Literal["gemini", "groq", "none"] = "none"
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-flash-lite-latest"  # Gemini text model (purpose, advisor)
    # Receipt photos. Live test 15 Nov 2026: flash-lite read a receipt in 1.5 s; gemini-flash-latest
    # answered 503 "high demand" / timed out on the free tier.
    LLM_VISION_MODEL: str = "gemini-flash-lite-latest"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"  # Groq text model (no receipt photos)
    LLM_TIMEOUT_SECONDS: int = 20
    AI_DAILY_LIMIT_ADVISOR: int = 30  # SUG-05
    AI_DAILY_LIMIT_EXTRACTION: int = 10
    AI_DAILY_LIMIT_PURPOSE: int = 10
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 5  # SUG-18
    FORECAST_WINDOW_WEEKS: int = 8  # SUG-07
    FORECAST_MIN_WEEKS: int = 4  # SUG-07
    HIGH_DEPENDENCY_SHARE: Decimal = Decimal("0.50")  # SUG-10
    # Daily automatic news collection inside the app (SUG-45); 0 = off (CLI `fetch-news` still works)
    NEWS_FETCH_HOURS: int = 0
    DEMO_PASSWORD: str = ""
    LOG_LEVEL: str = "INFO"
    # Built React app served by FastAPI (TRD §3 "Build"); empty = default path
    FRONTEND_DIST: str = ""

    @field_validator("LLM_MODEL", "LLM_VISION_MODEL", "GROQ_MODEL", mode="before")
    @classmethod
    def _blank_model_means_default(cls, v, info):
        # older .env files have "LLM_MODEL=" (empty); an empty model name would make every call fail
        return v.strip() if isinstance(v, str) and v.strip() else cls.model_fields[info.field_name].default

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def llm_status(self) -> str:
        if self.LLM_PROVIDER != "none" and (self.GEMINI_API_KEY or self.GROQ_API_KEY):
            return "configured"
        return "disabled"

    @property
    def frontend_dist_path(self) -> Path:
        return Path(self.FRONTEND_DIST) if self.FRONTEND_DIST else REPO_DIR / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
