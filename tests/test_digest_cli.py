import io
import json
import unittest
from unittest.mock import patch

from src.cli import digest


RESULT = {
    "report_path": "reports/daily/2026-05-19.md",
    "markdown": "# Digest",
    "profiles": [],
    "notification_channel": "markdown",
    "notification_result": "reports/daily/2026-05-19.md",
}


class DigestCliTests(unittest.TestCase):
    def test_run_prints_summary(self):
        stdout = io.StringIO()

        with patch("src.cli.digest.daily_job_digest", return_value=RESULT) as digest_mock:
            exit_code = digest.run([], stdout=stdout, stderr=io.StringIO())

        self.assertEqual(exit_code, 0)
        digest_mock.assert_called_once_with(
            resume_profile_id="default",
            limit_per_profile=5,
            top_n=5,
            exclude_seen=True,
            send_notification=True,
        )
        output = stdout.getvalue()
        self.assertIn("started_at=", output)
        self.assertIn("finished_at=", output)
        self.assertIn("duration_seconds=", output)
        self.assertIn("report_path=reports/daily/2026-05-19.md", output)
        self.assertIn("notification_channel=markdown", output)
        self.assertIn("notification_result=reports/daily/2026-05-19.md", output)

    def test_run_prints_json(self):
        stdout = io.StringIO()

        with patch("src.cli.digest.daily_job_digest", return_value=RESULT):
            exit_code = digest.run(["--json"], stdout=stdout, stderr=io.StringIO())

        self.assertEqual(exit_code, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual({key: output[key] for key in RESULT}, RESULT)
        self.assertIn("run", output)
        self.assertIn("started_at", output["run"])
        self.assertIn("finished_at", output["run"])
        self.assertIn("duration_seconds", output["run"])

    def test_run_passes_cli_options(self):
        with patch("src.cli.digest.daily_job_digest", return_value=RESULT) as digest_mock:
            exit_code = digest.run(
                ["--resume-profile-id", "senior", "--limit-per-profile", "3", "--top-n", "2", "--include-seen"],
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

        self.assertEqual(exit_code, 0)
        digest_mock.assert_called_once_with(
            resume_profile_id="senior",
            limit_per_profile=3,
            top_n=2,
            exclude_seen=False,
            send_notification=True,
        )

    def test_run_returns_error_for_digest_failure(self):
        stderr = io.StringIO()

        with patch("src.cli.digest.daily_job_digest", side_effect=RuntimeError("boom")):
            exit_code = digest.run([], stdout=io.StringIO(), stderr=stderr)

        self.assertEqual(exit_code, 1)
        self.assertIn("zighang-digest failed: RuntimeError: boom", stderr.getvalue())

    def test_run_dry_run_disables_notification_send(self):
        with patch("src.cli.digest.daily_job_digest", return_value=RESULT) as digest_mock:
            exit_code = digest.run(["--dry-run"], stdout=io.StringIO(), stderr=io.StringIO())

        self.assertEqual(exit_code, 0)
        digest_mock.assert_called_once_with(
            resume_profile_id="default",
            limit_per_profile=5,
            top_n=5,
            exclude_seen=True,
            send_notification=False,
        )


if __name__ == "__main__":
    unittest.main()
