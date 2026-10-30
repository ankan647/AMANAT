from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DEMO_MODE: bool = True
    JWT_SECRET: str = "change-me-demo-only"
    JWT_EXPIRE_MINUTES: int = 480
    DATABASE_URL: str = "sqlite:///./data/amanat.db"
    ANCHOR_DB_PATH: str = "./data/anchor_store.db"
    STORAGE_DIR: str = "./data/files"
    SIGNING_KEY_PATH: str = "./data/demo_ed25519.pem"
    SIM_START_DATE: date = date(2026, 10, 30)
    EXPIRING_WINDOW_DAYS: int = 60
    CONFIDENCE_HIGH_THRESHOLD: int = 80
    HIGH_VALUE_THRESHOLD_PAISE: int = 500_000_000
    CORS_ORIGINS: str = "http://localhost:5173"
    FRONTEND_BASE: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        Path(self.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        Path(self.ANCHOR_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.SIGNING_KEY_PATH).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
