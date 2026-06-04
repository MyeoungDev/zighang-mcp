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

    def test_render_daily_digest_adds_decision_sections_for_single_profile(self):
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

        self.assertIn("## 오늘의 최우선 공고", markdown)
        self.assertIn("## 새로 발견된 고득점 공고", markdown)
        self.assertIn("## 마감 임박", markdown)
        self.assertIn("## 필터별 추천: Backend", markdown)
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

        self.assertIn("## 오늘의 최우선 공고", markdown)
        self.assertIn("## 필터별 추천: Backend", markdown)
        self.assertIn("마감 상시채용", markdown)

    def test_render_daily_digest_surfaces_feedback_and_risk_sections(self):
        item = {
            "score": 82,
            "score_breakdown": {"feedback_affinity": 8},
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
            "mismatches": ["공고 키워드와 직접 겹치는 기술 스택이 적습니다."],
            "feedback_reasons": ["이전에 interested로 표시한 공고와 Java 항목이 유사합니다."],
        }

        markdown = render_daily_digest([{"profile_id": "backend", "name": "Backend", "recommendations": [item]}])

        self.assertIn("## 관심 공고와 유사", markdown)
        self.assertIn("피드백 근거: 이전에 interested", markdown)
        self.assertIn("## 확인 필요", markdown)


if __name__ == "__main__":
    unittest.main()
