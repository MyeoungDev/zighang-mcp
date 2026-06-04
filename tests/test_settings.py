import os
import tempfile
import unittest
from pathlib import Path

from src.config.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_load_settings_from_environment(self):
        old = os.environ.get("DEFAULT_PAGE_SIZE")
        os.environ["DEFAULT_PAGE_SIZE"] = "7"
        try:
            self.assertEqual(load_settings().default_page_size, 7)
        finally:
            if old is None:
                os.environ.pop("DEFAULT_PAGE_SIZE", None)
            else:
                os.environ["DEFAULT_PAGE_SIZE"] = old

    def test_load_email_settings_from_environment(self):
        keys = [
            "NOTIFICATION_CHANNELS",
            "NOTIFICATION_CHANNEL",
            "EMAIL_HOST",
            "EMAIL_PORT",
            "EMAIL_USERNAME",
            "EMAIL_PASSWORD",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "DISCORD_WEBHOOK_URL",
        ]
        old = {key: os.environ.get(key) for key in keys}
        os.environ.update(
            {
                "EMAIL_HOST": "smtp.example.com",
                "EMAIL_PORT": "2525",
                "EMAIL_USERNAME": "user",
                "EMAIL_PASSWORD": "pass",
                "TELEGRAM_BOT_TOKEN": "bot-token",
                "TELEGRAM_CHAT_ID": "chat-id",
                "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
                "NOTIFICATION_CHANNELS": "markdown,email",
            }
        )
        try:
            settings = load_settings()
            self.assertEqual(settings.notification_channel, "markdown,email")
            self.assertEqual(settings.email_host, "smtp.example.com")
            self.assertEqual(settings.email_port, 2525)
            self.assertEqual(settings.email_username, "user")
            self.assertEqual(settings.email_password, "pass")
            self.assertEqual(settings.telegram_bot_token, "bot-token")
            self.assertEqual(settings.telegram_chat_id, "chat-id")
            self.assertEqual(settings.discord_webhook_url, "https://discord.example/webhook")
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_load_settings_supports_legacy_notification_channel(self):
        keys = ["NOTIFICATION_CHANNELS", "NOTIFICATION_CHANNEL"]
        old = {key: os.environ.get(key) for key in keys}
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.environ.pop("NOTIFICATION_CHANNELS", None)
            os.environ["NOTIFICATION_CHANNEL"] = "telegram"
            try:
                settings = load_settings()
                self.assertEqual(settings.notification_channel, "telegram")
            finally:
                os.chdir(old_cwd)
                for key, value in old.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_load_settings_reads_dotenv_without_overriding_environment(self):
        keys = ["DEFAULT_PAGE_SIZE", "REQUEST_DELAY_MS"]
        old_env = {key: os.environ.get(key) for key in keys}
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".env").write_text("DEFAULT_PAGE_SIZE=11\nREQUEST_DELAY_MS=700\n", encoding="utf-8")
            os.environ["DEFAULT_PAGE_SIZE"] = "9"
            os.environ.pop("REQUEST_DELAY_MS", None)
            os.chdir(temp_path)
            try:
                settings = load_settings()
            finally:
                os.chdir(old_cwd)
                os.environ.pop("REQUEST_DELAY_MS", None)
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

        self.assertEqual(settings.default_page_size, 9)
        self.assertEqual(settings.request_delay_ms, 700)

    def test_load_settings_reads_job_detail_cache_settings(self):
        keys = ["JOB_DETAIL_CACHE_TTL_HOURS", "JOB_DETAIL_CACHE_MAX_ENTRIES"]
        old = {key: os.environ.get(key) for key in keys}
        os.environ["JOB_DETAIL_CACHE_TTL_HOURS"] = "6"
        os.environ["JOB_DETAIL_CACHE_MAX_ENTRIES"] = "25"
        try:
            settings = load_settings()
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(settings.job_detail_cache_ttl_hours, 6)
        self.assertEqual(settings.job_detail_cache_max_entries, 25)


if __name__ == "__main__":
    unittest.main()
