import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config.settings import Settings
from src.mcp.tools import jobs
from src.storage.db import JsonStore


class PreferenceAndTrackingTests(unittest.TestCase):
    def test_user_preferences_update_and_clear(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(data_dir=Path(temp_dir), reports_dir=Path(temp_dir) / "reports")

            with patch("src.mcp.tools.jobs.load_settings", return_value=settings):
                updated = jobs.update_user_preferences(
                    {
                        "preferred_job_categories": ["IT_개발"],
                        "excluded_keywords": ["인턴"],
                        "default_exclude_internships": False,
                    }
                )
                self.assertEqual(updated["preferred_job_categories"], ["IT_개발"])
                self.assertEqual(jobs.get_user_preferences()["excluded_keywords"], ["인턴"])

                cleared = jobs.clear_user_preferences()

            self.assertEqual(cleared["preferred_job_categories"], [])
            self.assertTrue(cleared["default_exclude_internships"])

    def test_update_user_preferences_from_text_extracts_common_job_preferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(data_dir=Path(temp_dir), reports_dir=Path(temp_dir) / "reports")

            with patch("src.mcp.tools.jobs.load_settings", return_value=settings):
                result = jobs.update_user_preferences_from_text(
                    "백엔드, 데이터 플랫폼, 서울/경기 정규직 위주. Spring Boot와 Airflow 경험을 살리고 인턴은 제외"
                )

            preferences = result["preferences"]

        self.assertEqual(preferences["preferred_job_categories"], ["IT_개발"])
        self.assertIn("서버_백엔드", preferences["preferred_job_subcategories"])
        self.assertIn("데이터엔지니어", preferences["preferred_job_subcategories"])
        self.assertEqual(preferences["preferred_regions"], ["경기", "서울"])
        self.assertEqual(preferences["preferred_employment_types"], ["정규직"])
        self.assertIn("Spring Boot", preferences["preferred_skills"])
        self.assertIn("Airflow", preferences["preferred_skills"])
        self.assertIn("인턴", preferences["excluded_keywords"])
        self.assertTrue(preferences["default_exclude_internships"])

    def test_update_user_preferences_from_text_can_replace_existing_preferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(data_dir=Path(temp_dir), reports_dir=Path(temp_dir) / "reports")

            with patch("src.mcp.tools.jobs.load_settings", return_value=settings):
                jobs.update_user_preferences({"preferred_regions": ["부산"], "preferred_skills": ["Java"]})
                result = jobs.update_user_preferences_from_text("DevOps/SRE, 경기, Docker", merge=False)

            preferences = result["preferences"]

        self.assertEqual(preferences["preferred_regions"], ["경기"])
        self.assertIn("DevOps_SRE", preferences["preferred_job_subcategories"])
        self.assertEqual(preferences["preferred_skills"], ["Docker"])
        self.assertNotIn("Java", preferences["preferred_skills"])

    def test_update_user_preferences_from_text_tracks_exclusions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(data_dir=Path(temp_dir), reports_dir=Path(temp_dir) / "reports")

            with patch("src.mcp.tools.jobs.load_settings", return_value=settings):
                result = jobs.update_user_preferences_from_text("프론트엔드는 제외하고 보안 쪽도 좋아")

            preferences = result["preferences"]

        self.assertIn("정보보호_보안", preferences["preferred_job_subcategories"])
        self.assertIn("프론트엔드", preferences["excluded_keywords"])
        self.assertIn("프론트엔드", preferences["disliked_keywords"])

    def test_tracking_aliases_share_local_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(data_dir=Path(temp_dir), reports_dir=Path(temp_dir) / "reports")

            with patch("src.mcp.tools.jobs.load_settings", return_value=settings):
                jobs.track_job_status("job-1", "interested", "check later")
                tracked = jobs.list_tracked_jobs()
                saved = jobs.list_saved_jobs()

            self.assertEqual(tracked, saved)
            self.assertEqual(tracked[0]["job_id"], "job-1")
            self.assertEqual(tracked[0]["status"], "interested")

    def test_digest_history_tracks_seen_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")

            history = store.update_digest_history(["job-1", "job-2"], "2026-05-21T09:00:00+09:00")
            history = store.update_digest_history(["job-2", "job-3"], "2026-05-21T10:00:00+09:00")

        self.assertEqual(history["last_run_at"], "2026-05-21T10:00:00+09:00")
        self.assertEqual(history["seen_job_ids"], ["job-1", "job-2", "job-3"])

    def test_partial_existing_state_merges_nested_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text('{"user_preferences": {"preferred_regions": ["서울"]}}', encoding="utf-8")

            preferences = JsonStore(path).get_user_preferences()

        self.assertEqual(preferences["preferred_regions"], ["서울"])
        self.assertEqual(preferences["excluded_keywords"], [])
        self.assertTrue(preferences["default_exclude_internships"])


if __name__ == "__main__":
    unittest.main()
