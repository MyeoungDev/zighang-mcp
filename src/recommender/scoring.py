from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from src.zighang.models import JobDetail, JobSummary

NEGATIVE_STATUSES = {"ignored", "rejected"}
LOW_PRIORITY_STATUSES = {"viewed", "applied"}
POSITIVE_STATUSES = {"bookmarked", "interested"}
FEEDBACK_POSITIVE_WEIGHTS = {"interested": 10, "bookmarked": 8, "applied": 6}
FEEDBACK_NEGATIVE_WEIGHTS = {"ignored": -10, "rejected": -8}


def _overlap(left: list[str], right: list[str]) -> set[str]:
    normalized = {item.lower(): item for item in left}
    matches = set()
    for item in right:
        lower = item.lower()
        for key, original in normalized.items():
            if key in lower or lower in key:
                matches.add(original)
    return matches



def _add_signal(signals: list[str], value: str | None) -> None:
    if value and value not in signals:
        signals.append(value)


def _job_text(job: JobSummary | JobDetail) -> str:
    parts = [job.title, job.company.name, *job.keywords, *job.tags, *job.depth_ones, *job.depth_twos, *job.depth_threes]
    if isinstance(job, JobDetail):
        parts.extend([job.summary_text, job.content_text])
    return "\n".join(part for part in parts if part)


def _feedback_terms(job: JobSummary | JobDetail) -> list[str]:
    return [
        *job.keywords,
        *job.tags,
        *job.depth_ones,
        *job.depth_twos,
        *job.depth_threes,
        *job.regions,
        *job.employee_types,
        job.title,
    ]


def _feedback_similarity(candidate: JobSummary | JobDetail, previous: JobSummary | JobDetail) -> tuple[int, list[str]]:
    candidate_terms = _feedback_terms(candidate)
    previous_terms = _feedback_terms(previous)
    matched_keywords = sorted(_overlap(candidate.keywords, previous.keywords))
    matched_jobs = sorted(_overlap(candidate.depth_ones + candidate.depth_twos + candidate.depth_threes, previous.depth_ones + previous.depth_twos + previous.depth_threes))
    matched_regions = sorted(_overlap(candidate.regions, previous.regions))
    matched_employment = sorted(_overlap(candidate.employee_types, previous.employee_types))
    matched_title_terms = sorted(_overlap([candidate.title], previous_terms) | _overlap([previous.title], candidate_terms))

    similarity = (
        min(6, len(matched_keywords) * 2)
        + min(5, len(matched_jobs) * 3)
        + min(3, len(matched_regions))
        + min(3, len(matched_employment))
        + min(3, len(matched_title_terms))
    )
    signals = [*matched_keywords[:3], *matched_jobs[:3], *matched_regions[:2], *matched_employment[:2], *matched_title_terms[:1]]
    return similarity, signals


def _feedback_adjustment(
    job: JobSummary | JobDetail,
    feedback_jobs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    affinity = 0
    penalty = 0
    reasons: list[str] = []
    warnings: list[str] = []
    if not feedback_jobs:
        return {"affinity": 0, "penalty": 0, "reasons": reasons, "warnings": warnings}

    for item in feedback_jobs:
        previous = item.get("job")
        status = item.get("status")
        if not isinstance(previous, JobSummary):
            continue
        similarity, signals = _feedback_similarity(job, previous)
        if similarity <= 0:
            continue
        signal_text = ", ".join(signals[:4]) if signals else "유사한 조건"
        if status in FEEDBACK_POSITIVE_WEIGHTS:
            delta = min(FEEDBACK_POSITIVE_WEIGHTS[status], similarity)
            affinity += delta
            if len(reasons) < 3:
                reasons.append(f"이전에 {status}로 표시한 공고와 {signal_text} 항목이 유사합니다.")
        elif status in FEEDBACK_NEGATIVE_WEIGHTS:
            delta = max(FEEDBACK_NEGATIVE_WEIGHTS[status], -similarity)
            penalty += delta
            if len(warnings) < 3:
                warnings.append(f"이전에 {status}로 표시한 공고와 {signal_text} 항목이 유사합니다.")

    return {
        "affinity": min(20, affinity),
        "penalty": max(-20, penalty),
        "reasons": reasons,
        "warnings": warnings,
    }


def _evidence_snippets(job: JobSummary | JobDetail, terms: list[str], limit: int = 5) -> list[str]:
    snippets: list[str] = []
    sources = [job.title, " / ".join(job.keywords), " / ".join(job.depth_twos or job.depth_ones)]
    if isinstance(job, JobDetail):
        sources.extend(re.split(r"[\n.。!?！？]", f"{job.summary_text}\n{job.content_text}"))
    normalized_terms = [term for term in terms if term]
    for source in sources:
        text = source.strip()
        if not text:
            continue
        text_lower = text.lower()
        if any(term.lower() in text_lower for term in normalized_terms):
            snippet = re.sub(r"\s+", " ", text)[:180]
            if snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def _saved_status_delta(saved_status: str | None) -> tuple[int, str | None]:
    if saved_status in NEGATIVE_STATUSES:
        return -35, f"이 공고는 이전에 {saved_status} 상태로 표시되었습니다."
    if saved_status in LOW_PRIORITY_STATUSES:
        return -10, f"이 공고는 이전에 {saved_status} 상태로 표시되었습니다."
    if saved_status in POSITIVE_STATUSES:
        return 10, f"이 공고는 이전에 {saved_status} 상태로 표시되었습니다."
    return 0, None

def deadline_bonus(end_date: str | None) -> tuple[int, str | None]:
    if not end_date:
        return 0, None
    try:
        days = (datetime.fromisoformat(end_date).date() - datetime.now().date()).days
    except ValueError:
        return 0, None
    if days < 0:
        return -20, "이미 마감된 공고로 보입니다."
    if days <= 3:
        return 12, "마감이 임박했습니다."
    if days <= 7:
        return 6, "일주일 내 마감입니다."
    return 0, None


def score_job(
    job: JobSummary | JobDetail,
    resume_profile: dict[str, Any] | None = None,
    saved_status: str | None = None,
    user_preferences: dict[str, Any] | None = None,
    feedback_jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile = resume_profile or {}
    preferences = user_preferences or {}
    skills = list(profile.get("skills") or [])
    projects = list(profile.get("projects") or [])
    profile_keywords = list(profile.get("keywords") or [])
    job_terms = job.keywords + job.tags + job.depth_ones + job.depth_twos + job.depth_threes + [job.title, job.company.name]
    full_text = _job_text(job)

    matched_skills = sorted(_overlap(skills, job_terms + [full_text]))
    matched_keywords = sorted(_overlap(profile_keywords, job_terms + [full_text]))[:10]
    matched_projects = [project for project in projects if _overlap([project], job_terms + [full_text])][:5]

    breakdown = {
        "base": 40,
        "resume_skills": min(35, len(matched_skills) * 8),
        "resume_keywords": min(15, len(matched_keywords) * 2),
        "resume_projects": min(10, len(matched_projects) * 3),
        "preferred_terms": 0,
        "preferred_category": 0,
        "preferred_region": 0,
        "preferred_employment": 0,
        "deadline": 0,
        "saved_status": 0,
        "feedback_affinity": 0,
        "feedback_penalty": 0,
        "penalties": 0,
    }
    score = breakdown["base"] + breakdown["resume_skills"] + breakdown["resume_keywords"] + breakdown["resume_projects"]

    matched_signals: list[str] = []
    for value in [*matched_skills, *matched_keywords, *matched_projects]:
        _add_signal(matched_signals, value)

    preference_reasons = []
    preference_warnings = []
    risk_flags = []
    preferred_terms = list(preferences.get("preferred_keywords") or []) + list(preferences.get("preferred_skills") or [])
    matched_preferred_terms = sorted(_overlap(preferred_terms, job_terms + [full_text]))[:8]
    matched_categories = sorted(_overlap(list(preferences.get("preferred_job_categories") or []), job.depth_ones))
    matched_subcategories = sorted(_overlap(list(preferences.get("preferred_job_subcategories") or []), job.depth_twos + job.depth_threes))
    matched_regions = sorted(_overlap(list(preferences.get("preferred_regions") or []), job.regions))
    matched_employment = sorted(_overlap(list(preferences.get("preferred_employment_types") or []), job.employee_types))

    if matched_preferred_terms:
        breakdown["preferred_terms"] = min(16, len(matched_preferred_terms) * 4)
        score += breakdown["preferred_terms"]
        preference_reasons.append(f"선호 키워드 {', '.join(matched_preferred_terms[:5])}가 공고와 겹칩니다.")
        for value in matched_preferred_terms:
            _add_signal(matched_signals, value)
    if matched_categories or matched_subcategories:
        breakdown["preferred_category"] = 8
        score += breakdown["preferred_category"]
        preference_reasons.append("선호 직무 카테고리와 맞습니다.")
        for value in [*matched_categories, *matched_subcategories]:
            _add_signal(matched_signals, value)
    if matched_regions:
        breakdown["preferred_region"] = 5
        score += breakdown["preferred_region"]
        preference_reasons.append(f"선호 지역 {', '.join(matched_regions[:3])}에 해당합니다.")
        for value in matched_regions:
            _add_signal(matched_signals, value)
    elif preferences.get("preferred_regions"):
        risk_flags.append("선호 지역과 일치하지 않습니다.")
    if matched_employment:
        breakdown["preferred_employment"] = 5
        score += breakdown["preferred_employment"]
        preference_reasons.append(f"선호 고용형태 {', '.join(matched_employment[:3])}에 해당합니다.")
        for value in matched_employment:
            _add_signal(matched_signals, value)
    elif preferences.get("preferred_employment_types"):
        risk_flags.append("선호 고용형태와 일치하지 않습니다.")

    disliked_terms = list(preferences.get("disliked_keywords") or [])
    matched_disliked_terms = sorted(_overlap(disliked_terms, job_terms + [full_text]))[:8]
    if matched_disliked_terms:
        penalty = min(24, len(matched_disliked_terms) * 8)
        breakdown["penalties"] -= penalty
        score -= penalty
        message = f"비선호 키워드 {', '.join(matched_disliked_terms[:5])}가 포함됩니다."
        preference_warnings.append(message)
        risk_flags.append(message)

    excluded_companies = [str(item).lower() for item in preferences.get("excluded_company_names") or []]
    if any(company and company in job.company.name.lower() for company in excluded_companies):
        breakdown["penalties"] -= 40
        score -= 40
        preference_warnings.append("제외 회사 목록에 포함된 회사입니다.")
        risk_flags.append("제외 회사 목록에 포함된 회사입니다.")

    bonus, deadline_reason = deadline_bonus(job.end_date)
    breakdown["deadline"] = bonus
    score += bonus
    if deadline_reason and bonus < 0:
        risk_flags.append(deadline_reason)
    elif deadline_reason:
        _add_signal(matched_signals, deadline_reason)

    saved_delta, saved_message = _saved_status_delta(saved_status)
    breakdown["saved_status"] = saved_delta
    score += saved_delta
    if saved_message and saved_delta < 0:
        risk_flags.append(saved_message)

    feedback = _feedback_adjustment(job, feedback_jobs)
    breakdown["feedback_affinity"] = feedback["affinity"]
    breakdown["feedback_penalty"] = feedback["penalty"]
    score += feedback["affinity"] + feedback["penalty"]
    preference_reasons.extend(feedback["reasons"])
    preference_warnings.extend(feedback["warnings"])
    risk_flags.extend(feedback["warnings"])

    if job.career_min is not None and job.career_min >= 5:
        risk_flags.append(f"요구 경력 하한 {job.career_min}년입니다.")
    if job.deadline_type:
        _add_signal(matched_signals, job.deadline_type)
    for value in [*job.depth_twos[:3], *job.regions[:3], *job.employee_types[:3], *job.keywords[:5]]:
        _add_signal(matched_signals, value)

    score = max(0, min(100, score))

    reasons = []
    if matched_skills:
        reasons.append(f"{', '.join(matched_skills)} 경험이 공고 키워드/직무와 연결됩니다.")
    if matched_keywords:
        reasons.append(f"이력서 키워드 {', '.join(matched_keywords[:5])}가 공고와 겹칩니다.")
    if deadline_reason:
        reasons.append(deadline_reason)
    if not reasons:
        reasons.append("명확한 기술 키워드 매칭은 적지만 직무/회사 정보를 기준으로 검토할 수 있습니다.")

    mismatches = []
    if saved_status in NEGATIVE_STATUSES:
        mismatches.append(f"이 공고는 이전에 {saved_status} 상태로 표시되었습니다.")
    if not matched_skills:
        mismatches.append("공고 키워드와 직접 겹치는 기술 스택이 적습니다.")

    evidence_terms = [*matched_signals, *matched_preferred_terms, *matched_skills, *matched_keywords]

    return {
        "job": job.to_dict(),
        "score": score,
        "score_breakdown": breakdown,
        "matched_signals": matched_signals[:20],
        "risk_flags": risk_flags[:10],
        "evidence_snippets": _evidence_snippets(job, evidence_terms),
        "detail_fetched": isinstance(job, JobDetail),
        "reasons": reasons,
        "mismatches": mismatches,
        "preference_reasons": preference_reasons,
        "preference_warnings": preference_warnings,
        "feedback_reasons": feedback["reasons"],
        "feedback_warnings": feedback["warnings"],
        "resume_highlights": matched_skills or matched_keywords[:5],
        "pre_apply_tips": [
            "공고의 담당업무와 직접 연결되는 프로젝트 성과를 이력서 상단에 배치하세요.",
            "요구 기술이 있다면 사용 기간과 운영 규모를 함께 적으세요.",
        ],
    }


def deduplicate_jobs(jobs: list[JobSummary]) -> list[JobSummary]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job.company.name.strip().lower(), job.title.strip().lower(), job.affiliate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique
