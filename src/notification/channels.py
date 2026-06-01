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
            raise ValueError("WEBHOOK_URL is required when NOTIFICATION_CHANNEL=webhook")

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
        sender: str | None,
        recipients: str | None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender or username
        self.recipients = [item.strip() for item in (recipients or "").split(",") if item.strip()]
        if not self.recipients and self.sender:
            self.recipients = [self.sender]

    def send(self, content: str) -> str:
        if not self.host:
            raise ValueError("EMAIL_HOST is required when NOTIFICATION_CHANNEL=email")
        if not self.sender:
            raise ValueError("EMAIL_FROM or EMAIL_USERNAME is required when NOTIFICATION_CHANNEL=email")
        if not self.recipients:
            raise ValueError("EMAIL_TO or EMAIL_USERNAME is required when NOTIFICATION_CHANNEL=email")

        message = EmailMessage()
        message["Subject"] = "Zighang Daily Job Digest"
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message.set_content(content)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.starttls()
                if self.username or self.password:
                    if not self.username or not self.password:
                        raise ValueError("EMAIL_USERNAME and EMAIL_PASSWORD must be provided together")
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
    email_from: str | None
    email_to: str | None


def build_notification_channel(settings: NotificationSettings, report_path: Path) -> NotificationChannel:
    channel = settings.notification_channel.lower()
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
            settings.email_from,
            settings.email_to,
        )
    raise ValueError(f"Unsupported NOTIFICATION_CHANNEL: {settings.notification_channel}")
