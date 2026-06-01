from __future__ import annotations

from src.recommender.scoring import score_job
from src.zighang.models import JobDetail


def explain_match(job: JobDetail, resume_profile: dict | None = None, saved_status: str | None = None, user_preferences: dict | None = None) -> dict:
    result = score_job(job, resume_profile, saved_status, user_preferences)
    result["application_strategy"] = [
        "상세 모집요강의 담당업무 문장을 이력서 프로젝트 설명과 1:1로 맞춰 보강하세요.",
        "부족한 항목은 숨기지 말고 유사 경험, 학습/운영 경험, 보완 계획으로 정리하세요.",
    ]
    return result
