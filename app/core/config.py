from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    app_tz: str = "Europe/Moscow"
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://academy:academy_secret@localhost:5432/academy_start"

    bot_token: str = ""
    bot_username: str = ""
    bot_webhook_url: str | None = None
    admin_telegram_ids: str = ""
    coach_telegram_ids: str = ""

    api_port: int = 8000
    site_port: int = 3001
    cors_origins: str = "*"

    @property
    def admin_ids(self) -> List[int]:
        if not self.admin_telegram_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()]

    @property
    def coach_ids(self) -> List[int]:
        if not self.coach_telegram_ids.strip():
            return []
        return [int(x.strip()) for x in self.coach_telegram_ids.split(",") if x.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env in ("local", "development")

    @property
    def bot_deep_link_base(self) -> str:
        username = (self.bot_username or "").lstrip("@")
        if not username:
            return "https://t.me/"
        return f"https://t.me/{username}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
