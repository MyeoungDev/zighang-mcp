import unittest

from src.notification.digest import render_daily_digest


class DigestTests(unittest.TestCase):
    def test_render_daily_digest_contains_profile_and_job(self):
        markdown = render_daily_digest(
            [
                {
                    "profile_id": "backend",
                    "name": "Backend",
                    "recommendations": [
                        {
                            "score": 90,
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
                    ],
                }
            ]
        )

        self.assertIn("Backend Engineer", markdown)
        self.assertIn("Java 경험이 맞습니다.", markdown)

    def test_render_daily_digest_avoids_duplicate_top_section_for_single_profile(self):
        markdown = render_daily_digest(
            [
                {
                    "profile_id": "backend",
                    "name": "Backend",
                    "recommendations": [
                        {
                            "score": 90,
                            "job": {
                                "id": "job-1",
                                "company_name": "Acme",
                                "title": "Backend Engineer",
                                "regions": ["서울"],
                                "deadline": {"end_date": "2026-06-30T23:59:59", "type": "마감일"},
                                "original_url": "https://zighang.com/recruitment/job-1",
                            },
                            "reasons": ["Java 경험이 맞습니다."],
                            "mismatches": [],
                        }
                    ],
                }
            ]
        )

        self.assertEqual(markdown.count("Backend Engineer"), 1)
        self.assertNotIn("## 필터:", markdown)
        self.assertIn("마감: 2026-06-30", markdown)
        self.assertNotIn("T23:59:59", markdown)

    def test_render_daily_digest_keeps_top_section_for_multiple_profiles(self):
        item = {
            "score": 90,
            "job": {
                "id": "job-1",
                "company_name": "Acme",
                "title": "Backend Engineer",
                "regions": ["서울"],
                "deadline": {"type": "상시채용"},
                "original_url": "https://zighang.com/recruitment/job-1",
            },
            "reasons": ["Java 경험이 맞습니다."],
            "mismatches": [],
        }

        markdown = render_daily_digest(
            [
                {"profile_id": "backend", "name": "Backend", "recommendations": [item]},
                {"profile_id": "data", "name": "Data", "recommendations": []},
            ]
        )

        self.assertIn("## 오늘 꼭 봐야 할 공고", markdown)
        self.assertIn("## 필터: Backend", markdown)
        self.assertIn("마감: 상시채용", markdown)


if __name__ == "__main__":
    unittest.main()
