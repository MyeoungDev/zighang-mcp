from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class NotificationChannel:
    def send(self, content: str) -> str:
        raise NotImplementedError


class NotificationFanoutChannel(NotificationChannel):
    def __init__(self, channels: list[tuple[str, NotificationChannel]]) -> None:
        self.channels = channels

    def send(self, content: str) -> str:
        results = []
        for name, channel in self.channels:
            results.append(f"{name}:{channel.send(content)}")
        return ",".join(results)


class ConsoleChannel(NotificationChannel):
    def send(self, content: str) -> str:
        print(content)
        return "console"


class MarkdownFileChannel(NotificationChannel):
    def __init__(self, path: Path) -> None:
        self.path = path

    def send(self, content: str) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        return str(self.path)


class WebhookChannel(NotificationChannel):
    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, content: str) -> str:
        if not self.url:
            raise ValueError("WEBHOOK_URL is required when NOTIFICATION_CHANNELS includes webhook")

        payload = json.dumps({"text": content}, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                status = getattr(response, "status", response.getcode())
                if status < 200 or status >= 300:
                    raise RuntimeError(f"Webhook delivery failed with HTTP {status}")
        except HTTPError as exc:
            raise RuntimeError(f"Webhook delivery failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Webhook delivery failed: {exc.reason}") from exc
        return "webhook"


class TelegramChannel(NotificationChannel):
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, content: str) -> str:
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required when NOTIFICATION_CHANNELS includes telegram")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required when NOTIFICATION_CHANNELS includes telegram")

        payload = json.dumps({"chat_id": self.chat_id, "text": content}, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                status = getattr(response, "status", response.getcode())
                if status < 200 or status >= 300:
                    raise RuntimeError(f"Telegram delivery failed with HTTP {status}")
        except HTTPError as exc:
            raise RuntimeError(f"Telegram delivery failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Telegram delivery failed: {exc.reason}") from exc
        return "telegram"


class DiscordChannel(NotificationChannel):
    def __init__(self, webhook_url: str | None) -> None:
        self.webhook_url = webhook_url

    def send(self, content: str) -> str:
        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL is required when NOTIFICATION_CHANNELS includes discord")

        payload = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                status = getattr(response, "status", response.getcode())
                if status < 200 or status >= 300:
                    raise RuntimeError(f"Discord delivery failed with HTTP {status}")
        except HTTPError as exc:
            raise RuntimeError(f"Discord delivery failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Discord delivery failed: {exc.reason}") from exc
        return "discord"


class SavedMarkdownChannel(NotificationChannel):
    def __init__(self, path: Path) -> None:
        self.path = path

    def send(self, content: str) -> str:
        return str(self.path)


class EmailChannel(NotificationChannel):
    def __init__(
        self,
        host: str | None,
        port: int,
        username: str | None,
        password: str | None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = username
        self.recipients = [username] if username else []

    def send(self, content: str) -> str:
        if not self.host:
            raise ValueError("EMAIL_HOST is required when NOTIFICATION_CHANNELS includes email")
        if not self.username:
            raise ValueError("EMAIL_USERNAME is required when NOTIFICATION_CHANNELS includes email")
        if not self.password:
            raise ValueError("EMAIL_PASSWORD is required when NOTIFICATION_CHANNELS includes email")

        message = EmailMessage()
        message["Subject"] = "Zighang Daily Job Digest"
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message.set_content(content)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.send_message(message, from_addr=self.sender, to_addrs=self.recipients)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Email delivery failed: {exc}") from exc
        return "email"


class NotificationSettings(Protocol):
    notification_channel: str
    webhook_url: str | None
    email_host: str | None
    email_port: int
    email_username: str | None
    email_password: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    discord_webhook_url: str | None


def _build_single_notification_channel(settings: NotificationSettings, report_path: Path, channel: str) -> NotificationChannel:
    if channel == "console":
        return ConsoleChannel()
    if channel == "markdown":
        return SavedMarkdownChannel(report_path)
    if channel == "webhook":
        return WebhookChannel(settings.webhook_url or "")
    if channel == "email":
        return EmailChannel(
            settings.email_host,
            settings.email_port,
            settings.email_username,
            settings.email_password,
        )
    if channel == "telegram":
        return TelegramChannel(settings.telegram_bot_token, settings.telegram_chat_id)
    if channel == "discord":
        return DiscordChannel(settings.discord_webhook_url)
    raise ValueError(f"Unsupported NOTIFICATION_CHANNELS value: {settings.notification_channel}")


def build_notification_channel(settings: NotificationSettings, report_path: Path) -> NotificationChannel:
    channel_names = [item.strip().lower() for item in settings.notification_channel.split(",") if item.strip()]
    if not channel_names:
        raise ValueError("NOTIFICATION_CHANNELS must include at least one channel")
    channels = [(name, _build_single_notification_channel(settings, report_path, name)) for name in channel_names]
    if len(channels) == 1:
        return channels[0][1]
    return NotificationFanoutChannel(channels)
