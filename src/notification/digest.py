from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any


def _format_deadline(deadline: dict[str, Any] | None) -> str:
    if not deadline:
        return "-"
    end_date = deadline.get("end_date")
    if isinstance(end_date, str) and end_date:
        return end_date.split("T", 1)[0]
    return deadline.get("type") or "-"


def _format_list(values: list[Any] | None, limit: int = 8) -> str:
    items = [str(value) for value in values or [] if value]
    if not items:
        return "-"
    visible = items[:limit]
    suffix = f" 외 {len(items) - limit}개" if len(items) > limit else ""
    return ", ".join(visible) + suffix


def _format_career(career: dict[str, Any] | None) -> str:
    if not career:
        return "-"
    minimum = career.get("min")
    maximum = career.get("max")
    if minimum is None and maximum is None:
        return "-"
    if minimum is None:
        return f"{maximum}년 이하"
    if maximum is None:
        return f"{minimum}년 이상"
    if minimum == maximum:
        return f"{minimum}년"
    return f"{minimum}-{maximum}년"


def _join_text(values: list[Any] | None, limit: int) -> str:
    items = [str(value).strip() for value in values or [] if str(value).strip()]
    return " / ".join(items[:limit])


def _deadline_days(deadline: dict[str, Any] | None) -> int | None:
    if not deadline:
        return None
    end_date = deadline.get("end_date")
    if not isinstance(end_date, str) or not end_date:
        return None
    try:
        return (datetime.fromisoformat(end_date).date() - date.today()).days
    except ValueError:
        return None


def _is_deadline_soon(job: dict[str, Any]) -> bool:
    days = _deadline_days(job.get("deadline"))
    return days is not None and 0 <= days <= 7


def _has_risk(item: dict[str, Any]) -> bool:
    return bool(item.get("risk_flags") or item.get("mismatches") or item.get("preference_warnings") or item.get("feedback_warnings"))


def _has_feedback_boost(item: dict[str, Any]) -> bool:
    breakdown = item.get("score_breakdown") or {}
    return bool(item.get("feedback_reasons")) or int(breakdown.get("feedback_affinity") or 0) > 0


def _append_summary_section(lines: list[str], title: str, items: list[tuple[str | None, dict[str, Any]]], limit: int = 3) -> None:
    lines.append(f"## {title}")
    if not items:
        lines.append("- 해당 공고가 없습니다.")
        lines.append("")
        return
    for profile_id, item in items[:limit]:
        job = item["job"]
        suffix = f" ({profile_id})" if profile_id else ""
        lines.append(f"- [{item.get('score', 0)}] {job['company_name']} - {job['title']}{suffix}")
        if item.get("feedback_reasons"):
            lines.append(f"  - 피드백 근거: {_join_text(item.get('feedback_reasons'), 1)}")
        elif item.get("reasons"):
            lines.append(f"  - 이유: {_join_text(item.get('reasons'), 1)}")
        if _has_risk(item):
            risks = [*(item.get("risk_flags") or []), *(item.get("mismatches") or []), *(item.get("feedback_warnings") or [])]
            lines.append(f"  - 확인 필요: {_join_text(risks, 1)}")
        lines.append(f"  - URL: {job['original_url']}")
    lines.append("")


def _append_job_decision_details(lines: list[str], item: dict[str, Any], job: dict[str, Any]) -> None:
    lines.append(
        "  - 조건: "
        f"지역 {_format_list(job.get('regions'), 4)} | "
        f"경력 {_format_career(job.get('career'))} | "
        f"고용 {_format_list(job.get('employment_types'), 4)} | "
        f"마감 {_format_deadline(job.get('deadline'))}"
    )
    lines.append(
        "  - 직무/키워드: "
        f"{_format_list(job.get('jobs'), 4)} | "
        f"{_format_list(job.get('keywords'), 6)}"
    )
    if item.get("matched_signals"):
        lines.append(f"  - 매칭 신호: {_format_list(item.get('matched_signals'), 10)}")
    if item.get("preference_reasons"):
        lines.append(f"  - 선호 근거: {_join_text(item.get('preference_reasons'), 2)}")
    if item.get("feedback_reasons"):
        lines.append(f"  - 피드백 근거: {_join_text(item.get('feedback_reasons'), 2)}")
    if item.get("reasons"):
        lines.append(f"  - 추천 이유: {_join_text(item.get('reasons'), 2)}")
    risks = [*(item.get("risk_flags") or []), *(item.get("mismatches") or []), *(item.get("feedback_warnings") or [])]
    if risks:
        lines.append(f"  - 확인 필요: {_join_text(risks, 3)}")
    if item.get("evidence_snippets"):
        lines.append(f"  - 공고 근거: {_join_text(item.get('evidence_snippets'), 3)}")
    if item.get("pre_apply_tips"):
        lines.append(f"  - 지원 전 체크: {_join_text(item.get('pre_apply_tips'), 2)}")
    lines.append(f"  - URL: {job['original_url']}")


def render_daily_digest(results_by_profile: list[dict[str, Any]], top_n: int = 5) -> str:
    all_items = []
    for profile in results_by_profile:
        for item in profile.get("recommendations", []):
            all_items.append((profile.get("profile_id"), item))
    top_items = sorted(all_items, key=lambda pair: pair[1].get("score", 0), reverse=True)[:top_n]
    new_high_score_items = [pair for pair in top_items if pair[1].get("score", 0) >= 70]
    deadline_soon_items = [pair for pair in all_items if _is_deadline_soon(pair[1].get("job") or {})]
    feedback_items = [pair for pair in all_items if _has_feedback_boost(pair[1])]
    risk_items = [pair for pair in all_items if _has_risk(pair[1])]

    lines = [f"# Zighang Daily Job Digest - {date.today().isoformat()}", ""]
    _append_summary_section(lines, "오늘의 최우선 공고", top_items, top_n)
    _append_summary_section(lines, "새로 발견된 고득점 공고", new_high_score_items, top_n)
    _append_summary_section(lines, "마감 임박", deadline_soon_items, top_n)
    _append_summary_section(lines, "관심 공고와 유사", feedback_items, top_n)
    _append_summary_section(lines, "확인 필요", risk_items, top_n)

    for profile in results_by_profile:
        heading = f"필터별 추천: {profile.get('name') or profile.get('profile_id')}"
        lines.append(f"## {heading}")
        recommendations = profile.get("recommendations", [])
        if not recommendations:
            lines.append("- 추천 공고가 없습니다.")
            continue
        for item in recommendations:
            job = item["job"]
            lines.append(f"- [{item['score']}] {job['company_name']} - {job['title']}")
            _append_job_decision_details(lines, item, job)
    lines.append("")
    return "\n".join(lines)


def render_digest_setup_required() -> str:
    return "\n".join(
        [
            f"# Zighang Daily Job Digest - {date.today().isoformat()}",
            "",
            "## 설정이 필요합니다",
            "- 활성화된 필터 프로필이 없어 추천 공고를 생성하지 못했습니다.",
            "- MCP에서 `save_filter_profile`을 먼저 호출해 관심 직무, 지역, 고용형태 같은 조건을 저장하세요.",
            "- 예: `profile_id=backend`, `name=Backend`, `notifications_enabled=true`, `filters={...}`",
            "",
        ]
    )


def save_daily_digest(markdown: str, reports_dir: Path = Path("reports/daily")) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{date.today().isoformat()}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
