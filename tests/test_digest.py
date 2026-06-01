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


if __name__ == "__main__":
    unittest.main()

