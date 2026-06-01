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
                                "career": {"min": 3, "max": 7},
                                "employment_types": ["정규직"],
                                "jobs": ["서버_백엔드"],
                                "keywords": ["Spring Boot"],
                                "original_url": "https://zighang.com/recruitment/job-1",
                            },
                            "reasons": ["Java 경험이 맞습니다."],
                            "mismatches": [],
                            "matched_signals": ["Java", "Spring Boot"],
                            "preference_reasons": ["선호 직무 카테고리와 맞습니다."],
                            "evidence_snippets": ["Spring Boot 기반 API 개발"],
                            "pre_apply_tips": ["운영 경험을 이력서 상단에 배치하세요."],
                        }
                    ],
                }
            ]
        )

        self.assertIn("Backend Engineer", markdown)
        self.assertIn("Java 경험이 맞습니다.", markdown)
        self.assertIn("조건: 지역 서울 | 경력 3-7년 | 고용 정규직 | 마감 2026-05-30", markdown)
        self.assertIn("직무/키워드: 서버_백엔드 | Spring Boot", markdown)
        self.assertIn("매칭 신호: Java, Spring Boot", markdown)
        self.assertIn("선호 근거: 선호 직무 카테고리와 맞습니다.", markdown)
        self.assertIn("공고 근거: Spring Boot 기반 API 개발", markdown)
        self.assertIn("지원 전 체크: 운영 경험을 이력서 상단에 배치하세요.", markdown)

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
                                "career": {"min": 3, "max": 7},
                                "employment_types": ["정규직"],
                                "jobs": ["서버_백엔드"],
                                "keywords": ["Java"],
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
        self.assertIn("마감 2026-06-30", markdown)
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
                "career": {"min": 3, "max": 7},
                "employment_types": ["정규직"],
                "jobs": ["서버_백엔드"],
                "keywords": ["Java"],
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
        self.assertIn("마감 상시채용", markdown)


if __name__ == "__main__":
    unittest.main()
