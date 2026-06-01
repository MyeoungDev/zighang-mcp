import os
import unittest

from src.config.settings import load_settings
from src.notification.channels import EmailChannel, WebhookChannel


@unittest.skipUnless(os.getenv("RUN_LIVE_NOTIFICATION_TESTS") == "1", "live notification smoke tests are opt-in")
class LiveNotificationSmokeTests(unittest.TestCase):
    def test_live_webhook_delivery(self):
        settings = load_settings()
        if not settings.webhook_url:
            self.skipTest("WEBHOOK_URL is required for live webhook smoke test")

        result = WebhookChannel(settings.webhook_url).send("# Zighang live notification smoke test\n- webhook")

        self.assertEqual(result, "webhook")

    def test_live_email_delivery(self):
        settings = load_settings()
        missing = [
            name
            for name, value in [
                ("EMAIL_HOST", settings.email_host),
                ("EMAIL_USERNAME", settings.email_username),
                ("EMAIL_PASSWORD", settings.email_password),
            ]
            if not value
        ]
        if missing:
            self.skipTest(f"{', '.join(missing)} required for live email smoke test")

        result = EmailChannel(
            settings.email_host,
            settings.email_port,
            settings.email_username,
            settings.email_password,
        ).send("# Zighang live notification smoke test\n- email")

        self.assertEqual(result, "email")


if __name__ == "__main__":
    unittest.main()
