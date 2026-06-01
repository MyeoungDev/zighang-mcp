import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from src.config.settings import Settings
from src.notification.channels import DiscordChannel, EmailChannel, TelegramChannel, WebhookChannel, build_notification_channel


class FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self):
        return self.status


class NotificationChannelTests(unittest.TestCase):
    def test_webhook_channel_posts_markdown_as_json_text(self):
        with patch("src.notification.channels.urlopen", return_value=FakeResponse(204)) as urlopen_mock:
            result = WebhookChannel("https://example.com/webhook").send("# Digest\n- Job")

        self.assertEqual(result, "webhook")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/webhook")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Content-type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"text": "# Digest\n- Job"})

    def test_webhook_channel_rejects_missing_url(self):
        with self.assertRaisesRegex(ValueError, "WEBHOOK_URL"):
            WebhookChannel("").send("content")

    def test_webhook_channel_rejects_http_error(self):
        error = HTTPError("https://example.com/webhook", 500, "server error", hdrs=None, fp=None)
        with patch("src.notification.channels.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 500"):
                WebhookChannel("https://example.com/webhook").send("content")

    def test_build_notification_channel_uses_webhook_settings(self):
        settings = Settings(notification_channel="webhook", webhook_url="https://example.com/webhook")

        channel = build_notification_channel(settings, Path("reports/daily/report.md"))

        self.assertIsInstance(channel, WebhookChannel)
        self.assertEqual(channel.url, "https://example.com/webhook")

    def test_build_notification_channel_rejects_unknown_channel(self):
        settings = Mock(notification_channel="sms", webhook_url=None)

        with self.assertRaisesRegex(ValueError, "Unsupported NOTIFICATION_CHANNEL"):
            build_notification_channel(settings, Path("reports/daily/report.md"))

    def test_email_channel_sends_markdown_with_starttls_and_login(self):
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)

        with patch("src.notification.channels.smtplib.SMTP", return_value=smtp) as smtp_class:
            result = EmailChannel(
                host="smtp.example.com",
                port=587,
                username="user@example.com",
                password="pass",
            ).send("# Digest\n- Job")

        self.assertEqual(result, "email")
        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("user@example.com", "pass")
        smtp.send_message.assert_called_once()
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["Subject"], "Zighang Daily Job Digest")
        self.assertEqual(message["From"], "user@example.com")
        self.assertEqual(message["To"], "user@example.com")
        self.assertIn("# Digest", message.get_content())
        self.assertEqual(smtp.send_message.call_args.kwargs["from_addr"], "user@example.com")
        self.assertEqual(smtp.send_message.call_args.kwargs["to_addrs"], ["user@example.com"])

    def test_email_channel_rejects_missing_required_settings(self):
        with self.assertRaisesRegex(ValueError, "EMAIL_HOST"):
            EmailChannel(None, 587, "user@example.com", "pass").send("content")
        with self.assertRaisesRegex(ValueError, "EMAIL_USERNAME"):
            EmailChannel("smtp.example.com", 587, None, "pass").send("content")
        with self.assertRaisesRegex(ValueError, "EMAIL_PASSWORD"):
            EmailChannel("smtp.example.com", 587, "user@example.com", None).send("content")

    def test_email_channel_wraps_smtp_errors(self):
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)
        smtp.send_message.side_effect = Exception("boom")

        with patch("src.notification.channels.smtplib.SMTP", return_value=smtp):
            with self.assertRaisesRegex(RuntimeError, "Email delivery failed"):
                EmailChannel("smtp.example.com", 587, "user@example.com", "pass").send("content")

    def test_build_notification_channel_uses_email_settings(self):
        settings = Settings(
            notification_channel="email",
            email_host="smtp.example.com",
            email_port=587,
            email_username="user@example.com",
            email_password="pass",
        )

        channel = build_notification_channel(settings, Path("reports/daily/report.md"))

        self.assertIsInstance(channel, EmailChannel)
        self.assertEqual(channel.host, "smtp.example.com")
        self.assertEqual(channel.recipients, ["user@example.com"])

    def test_telegram_channel_sends_message(self):
        with patch("src.notification.channels.urlopen", return_value=FakeResponse(200)) as urlopen_mock:
            result = TelegramChannel("token", "chat-id").send("# Digest")

        self.assertEqual(result, "telegram")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.telegram.org/bottoken/sendMessage")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"chat_id": "chat-id", "text": "# Digest"})

    def test_telegram_channel_rejects_missing_settings(self):
        with self.assertRaisesRegex(ValueError, "TELEGRAM_BOT_TOKEN"):
            TelegramChannel(None, "chat-id").send("content")
        with self.assertRaisesRegex(ValueError, "TELEGRAM_CHAT_ID"):
            TelegramChannel("token", None).send("content")

    def test_discord_channel_sends_message(self):
        with patch("src.notification.channels.urlopen", return_value=FakeResponse(204)) as urlopen_mock:
            result = DiscordChannel("https://discord.example/webhook").send("# Digest")

        self.assertEqual(result, "discord")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://discord.example/webhook")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"content": "# Digest"})

    def test_discord_channel_rejects_missing_webhook(self):
        with self.assertRaisesRegex(ValueError, "DISCORD_WEBHOOK_URL"):
            DiscordChannel(None).send("content")

    def test_build_notification_channel_uses_telegram_settings(self):
        settings = Settings(notification_channel="telegram", telegram_bot_token="token", telegram_chat_id="chat-id")

        channel = build_notification_channel(settings, Path("reports/daily/report.md"))

        self.assertIsInstance(channel, TelegramChannel)
        self.assertEqual(channel.bot_token, "token")
        self.assertEqual(channel.chat_id, "chat-id")

    def test_build_notification_channel_uses_discord_settings(self):
        settings = Settings(notification_channel="discord", discord_webhook_url="https://discord.example/webhook")

        channel = build_notification_channel(settings, Path("reports/daily/report.md"))

        self.assertIsInstance(channel, DiscordChannel)
        self.assertEqual(channel.webhook_url, "https://discord.example/webhook")


if __name__ == "__main__":
    unittest.main()
