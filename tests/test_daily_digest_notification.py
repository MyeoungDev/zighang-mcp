import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config.settings import Settings
from src.mcp.tools import jobs
from src.storage.db import JsonStore


class DailyDigestNotificationTests(unittest.TestCase):
    def test_daily_job_digest_reports_setup_required_without_filter_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports", notification_channel="markdown")

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs") as recommend_mock,
            ):
                result = jobs.daily_job_digest(include_pinned=False)

            self.assertTrue(result["setup_required"])
            self.assertIn("save_filter_profile", result["setup_message"])
            self.assertIn("설정이 필요합니다", result["markdown"])
            self.assertEqual(result["notification_result"], result["report_path"])
            self.assertTrue(Path(result["report_path"]).exists())
            recommend_mock.assert_not_called()

    def test_daily_job_digest_sends_webhook_after_saving_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            store.upsert_filter_profile("backend", {"name": "Backend", "filters": {}, "notifications_enabled": True})
            settings = Settings(
                data_dir=temp_path,
                reports_dir=temp_path / "reports",
                notification_channel="webhook",
                webhook_url="https://example.com/webhook",
            )
            recommendation = {
                "score": 91,
                "job": {
                    "id": "job-1",
                    "company_name": "Acme",
                    "title": "Backend Engineer",
                    "regions": ["서울"],
                    "deadline": {"end_date": "2026-05-30"},
                    "original_url": "https://zighang.com/recruitment/job-1",
                },
                "reasons": ["Java 경험이 맞습니다."],
                "mismatches": [],
            }

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": [recommendation]}),
                patch("src.notification.channels.WebhookChannel.send", return_value="webhook") as send_mock,
            ):
                result = jobs.daily_job_digest(include_pinned=False)

            self.assertEqual(result["notification_channel"], "webhook")
            self.assertEqual(result["notification_result"], "webhook")
            self.assertTrue(Path(result["report_path"]).exists())
            send_mock.assert_called_once()
            self.assertIn("Backend Engineer", send_mock.call_args.args[0])

    def test_daily_job_digest_keeps_markdown_default_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports", notification_channel="markdown")

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": []}),
            ):
                result = jobs.daily_job_digest(include_pinned=False)

            self.assertEqual(result["notification_channel"], "markdown")
            self.assertEqual(result["notification_result"], result["report_path"])
            self.assertTrue(Path(result["report_path"]).exists())

    def test_daily_job_digest_sends_email_after_saving_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            store.upsert_filter_profile("backend", {"name": "Backend", "filters": {}, "notifications_enabled": True})
            settings = Settings(
                data_dir=temp_path,
                reports_dir=temp_path / "reports",
                notification_channel="email",
                email_host="smtp.example.com",
                email_username="user@example.com",
                email_password="pass",
            )

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": []}),
                patch("src.notification.channels.EmailChannel.send", return_value="email") as send_mock,
            ):
                result = jobs.daily_job_digest(include_pinned=False)

            self.assertEqual(result["notification_channel"], "email")
            self.assertEqual(result["notification_result"], "email")
            self.assertTrue(Path(result["report_path"]).exists())
            send_mock.assert_called_once()

    def test_daily_job_digest_dry_run_skips_notification_send(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            store.upsert_filter_profile("backend", {"name": "Backend", "filters": {}, "notifications_enabled": True})
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports", notification_channel="webhook", webhook_url="https://example.com/webhook")
            recommendation = {
                "score": 91,
                "job": {
                    "id": "job-1",
                    "company_name": "Acme",
                    "title": "Backend Engineer",
                    "regions": ["서울"],
                    "deadline": {"end_date": "2026-05-30"},
                    "original_url": "https://zighang.com/recruitment/job-1",
                },
                "reasons": ["Java 경험이 맞습니다."],
                "mismatches": [],
            }

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": [recommendation]}),
                patch("src.notification.channels.WebhookChannel.send") as send_mock,
            ):
                result = jobs.daily_job_digest(send_notification=False, include_pinned=False)

            self.assertEqual(result["notification_channel"], "webhook")
            self.assertEqual(result["notification_result"], "dry-run")
            self.assertTrue(Path(result["report_path"]).exists())
            self.assertEqual(result["digest_history"]["seen_job_ids"], [])
            send_mock.assert_not_called()

    def test_daily_job_digest_does_not_update_history_when_notification_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            store.upsert_filter_profile("backend", {"name": "Backend", "filters": {}, "notifications_enabled": True})
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports", notification_channel="webhook", webhook_url="https://example.com/webhook")
            recommendation = {
                "score": 91,
                "job": {
                    "id": "job-1",
                    "company_name": "Acme",
                    "title": "Backend Engineer",
                    "regions": ["서울"],
                    "deadline": {"end_date": "2026-05-30"},
                    "original_url": "https://zighang.com/recruitment/job-1",
                },
                "reasons": ["Java 경험이 맞습니다."],
                "mismatches": [],
            }

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": [recommendation]}),
                patch("src.notification.channels.WebhookChannel.send", side_effect=RuntimeError("delivery failed")),
            ):
                with self.assertRaisesRegex(RuntimeError, "delivery failed"):
                    jobs.daily_job_digest(include_pinned=False)

            self.assertEqual(store.load()["digest_history"]["seen_job_ids"], [])


if __name__ == "__main__":
    unittest.main()
