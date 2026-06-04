import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.config.settings import Settings
from src.mcp.tools import jobs
from src.storage.db import JsonStore


def recommendation(job_id: str, score: int, company: str = "Acme", keyword: str = "Java") -> dict:
    return {
        "score": score,
        "job": {
            "id": job_id,
            "company_name": company,
            "title": f"{keyword} Backend Engineer",
            "regions": ["서울"],
            "deadline": {"end_date": "2026-06-07"},
            "career": {"min": 3, "max": 7},
            "employment_types": ["정규직"],
            "jobs": ["서버_백엔드"],
            "keywords": [keyword, "Spring"],
            "original_url": f"https://zighang.com/recruitment/{job_id}",
        },
        "matched_signals": [keyword, "서울"],
        "risk_flags": ["요구 경력 하한 3년입니다."] if score < 70 else [],
        "mismatches": ["공고 키워드와 직접 겹치는 기술 스택이 적습니다."] if score < 70 else [],
        "pre_apply_tips": ["운영 규모를 이력서에 보강하세요."],
        "reasons": [f"{keyword} 경험이 맞습니다."],
    }


class DigestAnalyticsTests(unittest.TestCase):
    def test_daily_digest_saves_snapshot_and_job_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            store.upsert_filter_profile("backend", {"name": "Backend", "filters": {}, "notifications_enabled": True})
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports", notification_channel="markdown")

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs._today_seoul", return_value=date(2026, 6, 4)),
                patch("src.mcp.tools.jobs.recommend_jobs", return_value={"recommendations": [recommendation("job-1", 91)]}),
            ):
                result = jobs.daily_job_digest(include_pinned=False)

            state = store.load()

        self.assertEqual(result["snapshot_date"], "2026-06-04")
        self.assertIn("2026-06-04", state["daily_snapshots"])
        self.assertEqual(state["daily_snapshots"]["2026-06-04"]["high_score_jobs"], 1)
        self.assertEqual(state["job_history"]["job-1"]["first_seen_date"], "2026-06-04")
        self.assertEqual(state["job_history"]["job-1"]["seen_count"], 1)

    def test_job_history_accumulates_repeated_jobs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            first = {
                "date": "2026-06-03",
                "jobs": [recommendation("job-1", 60)["job"] | {"score": 60, "risk_flags": [], "mismatches": [], "pre_apply_tips": []}],
            }
            second = {
                "date": "2026-06-04",
                "jobs": [recommendation("job-1", 88)["job"] | {"score": 88, "risk_flags": [], "mismatches": [], "pre_apply_tips": []}],
            }
            store.save_digest_snapshot("2026-06-03", first)
            store.save_digest_snapshot("2026-06-04", second)
            history = store.load()["job_history"]

        self.assertEqual(history["job-1"]["first_seen_date"], "2026-06-03")
        self.assertEqual(history["job-1"]["last_seen_date"], "2026-06-04")
        self.assertEqual(history["job-1"]["seen_count"], 2)
        self.assertEqual(history["job-1"]["best_score"], 88)
        self.assertEqual(history["job-1"]["latest_score"], 88)

    def test_weekly_summary_trends_and_gap_tools_read_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = JsonStore(temp_path / "state.json")
            settings = Settings(data_dir=temp_path, reports_dir=temp_path / "reports")
            store.save_digest_snapshot(
                "2026-05-28",
                {
                    "date": "2026-05-28",
                    "jobs": [recommendation("old-1", 80, company="OldCo", keyword="Python")["job"] | {"score": 80, "risk_flags": [], "mismatches": [], "pre_apply_tips": []}],
                },
            )
            store.save_digest_snapshot(
                "2026-06-03",
                {
                    "date": "2026-06-03",
                    "jobs": [recommendation("job-1", 91, company="Acme", keyword="Java")["job"] | {"score": 91, "risk_flags": [], "mismatches": [], "pre_apply_tips": []}],
                },
            )
            store.save_digest_snapshot(
                "2026-06-04",
                {
                    "date": "2026-06-04",
                    "jobs": [
                        recommendation("job-2", 62, company="Beta", keyword="Kubernetes")["job"]
                        | {
                            "score": 62,
                            "risk_flags": ["선호 지역과 일치하지 않습니다."],
                            "mismatches": ["공고 키워드와 직접 겹치는 기술 스택이 적습니다."],
                            "pre_apply_tips": ["Kubernetes 운영 경험을 보강하세요."],
                        }
                    ],
                },
            )

            with (
                patch("src.mcp.tools.jobs.load_settings", return_value=settings),
                patch("src.mcp.tools.jobs._today_seoul", return_value=date(2026, 6, 4)),
            ):
                history = jobs.get_digest_history(days=2)
                weekly = jobs.get_weekly_job_summary()
                trends = jobs.get_job_market_trends(days=1)
                gaps = jobs.get_resume_gap_analysis(days=2)

        self.assertEqual(history["snapshot_count"], 2)
        self.assertFalse(weekly["insufficient_data"])
        self.assertEqual(weekly["total_jobs"], 2)
        self.assertEqual(weekly["high_score_jobs"], 1)
        self.assertTrue(trends["comparison_available"])
        self.assertIn("keyword_changes", trends)
        self.assertFalse(gaps["insufficient_data"])
        self.assertEqual(gaps["analyzed_jobs"], 2)
        self.assertTrue(gaps["top_gap_signals"])


if __name__ == "__main__":
    unittest.main()
