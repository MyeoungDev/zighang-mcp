from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env_file() -> None:
    load_dotenv(Path.cwd() / ".env", override=False)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    zighang_base_url: str = "https://api.zighang.com/api"
    zighang_auth_token: str | None = None
    zighang_cookie: str | None = None
    default_page_size: int = 20
    request_delay_ms: int = 300
    resume_path: Path = Path("resumes/resume.md")
    portfolio_path: Path = Path("portfolios/portfolio.md")
    notification_channel: str = "markdown"
    webhook_url: str | None = None
    email_host: str | None = None
    email_port: int = 587
    email_username: str | None = None
    email_password: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    data_dir: Path = Path("data/cache")
    reports_dir: Path = Path("reports/daily")


def load_settings() -> Settings:
    _load_env_file()
    return Settings(
        zighang_base_url=os.getenv("ZIGHANG_BASE_URL", "https://api.zighang.com/api").rstrip("/"),
        zighang_auth_token=os.getenv("ZIGHANG_AUTH_TOKEN") or None,
        zighang_cookie=os.getenv("ZIGHANG_COOKIE") or None,
        default_page_size=_get_int("DEFAULT_PAGE_SIZE", 20),
        request_delay_ms=_get_int("REQUEST_DELAY_MS", 300),
        resume_path=Path(os.getenv("RESUME_PATH", "resumes/resume.md")),
        portfolio_path=Path(os.getenv("PORTFOLIO_PATH", "portfolios/portfolio.md")),
        notification_channel=os.getenv("NOTIFICATION_CHANNEL", "markdown"),
        webhook_url=os.getenv("WEBHOOK_URL") or None,
        email_host=os.getenv("EMAIL_HOST") or None,
        email_port=_get_int("EMAIL_PORT", 587),
        email_username=os.getenv("EMAIL_USERNAME") or None,
        email_password=os.getenv("EMAIL_PASSWORD") or None,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
        data_dir=Path(os.getenv("DATA_DIR", "data/cache")),
        reports_dir=Path(os.getenv("REPORTS_DIR", "reports/daily")),
    )
