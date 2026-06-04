import json
import unittest
from pathlib import Path

from src.recommender.scoring import deduplicate_jobs, score_job
from src.zighang.models import JobDetail, JobSummary


FIXTURES = Path(__file__).parent / "fixtures"


class ScoringTests(unittest.TestCase):
    def test_recommendation_score_uses_skill_overlap(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        job = JobSummary.from_api(data)
        profile = {"skills": ["Java", "Spring Boot", "Kafka"], "keywords": ["API", "PostgreSQL"], "projects": []}

        result = score_job(job, profile)

        self.assertGreaterEqual(result["score"], 55)
        self.assertIn("Java", result["resume_highlights"])
        self.assertTrue(result["reasons"])

    def test_user_preferences_adjust_score_and_explanations(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        job = JobSummary.from_api(data)

        result = score_job(
            job,
            {"skills": [], "keywords": [], "projects": []},
            user_preferences={
                "preferred_job_categories": job.depth_ones,
                "preferred_regions": job.regions,
                "preferred_keywords": job.keywords[:1],
                "disliked_keywords": ["unmatched"],
            },
        )

        self.assertGreater(result["score"], 40)
        self.assertTrue(result["preference_reasons"])
        self.assertEqual(result["preference_warnings"], [])

    def test_user_preferences_penalize_disliked_keywords(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        job = JobSummary.from_api(data)

        result = score_job(
            job,
            {"skills": [], "keywords": [], "projects": []},
            user_preferences={"disliked_keywords": job.keywords[:1]},
        )

        self.assertLess(result["score"], 40)
        self.assertTrue(result["preference_warnings"])

    def test_feedback_jobs_adjust_score_with_explanations(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        job = JobSummary.from_api(data)

        positive = score_job(
            job,
            {"skills": [], "keywords": [], "projects": []},
            feedback_jobs=[{"status": "interested", "job": job}],
        )
        negative = score_job(
            job,
            {"skills": [], "keywords": [], "projects": []},
            feedback_jobs=[{"status": "ignored", "job": job}],
        )

        self.assertGreater(positive["score_breakdown"]["feedback_affinity"], 0)
        self.assertTrue(positive["feedback_reasons"])
        self.assertLess(negative["score_breakdown"]["feedback_penalty"], 0)
        self.assertTrue(negative["feedback_warnings"])

    def test_score_job_returns_structured_evidence_for_detail(self):
        data = json.loads((FIXTURES / "job_detail.json").read_text(encoding="utf-8"))
        job = JobDetail.from_api(data)

        result = score_job(
            job,
            {"skills": ["Spring Boot"], "keywords": ["API"], "projects": []},
            user_preferences={"preferred_regions": ["부산"], "preferred_employment_types": ["정규직"]},
        )

        self.assertTrue(result["detail_fetched"])
        self.assertIn("score_breakdown", result)
        self.assertIn("Spring Boot", result["matched_signals"])
        self.assertTrue(result["evidence_snippets"])
        self.assertIn("선호 지역과 일치하지 않습니다.", result["risk_flags"])
        self.assertGreater(result["score_breakdown"]["resume_skills"], 0)

    def test_score_job_surfaces_penalty_risks(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        job = JobSummary.from_api(data)

        result = score_job(
            job,
            {"skills": [], "keywords": [], "projects": []},
            saved_status="ignored",
            user_preferences={"disliked_keywords": ["Java"], "excluded_company_names": ["Acme"]},
        )

        self.assertFalse(result["detail_fetched"])
        self.assertLess(result["score_breakdown"]["penalties"], 0)
        self.assertTrue(any("비선호 키워드" in flag for flag in result["risk_flags"]))
        self.assertTrue(any("제외 회사" in flag for flag in result["risk_flags"]))
        self.assertTrue(any("ignored" in flag for flag in result["risk_flags"]))

    def test_deduplicate_jobs_uses_company_title_affiliate(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))["content"][0]
        first = JobSummary.from_api(data)
        second = JobSummary.from_api(data)

        self.assertEqual(len(deduplicate_jobs([first, second])), 1)


if __name__ == "__main__":
    unittest.main()
