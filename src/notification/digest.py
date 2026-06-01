from __future__ import annotations

from datetime import date
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
    if item.get("reasons"):
        lines.append(f"  - 추천 이유: {_join_text(item.get('reasons'), 2)}")
    risks = [*(item.get("risk_flags") or []), *(item.get("mismatches") or [])]
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

    lines = [f"# Zighang Daily Job Digest - {date.today().isoformat()}", ""]
    if len(results_by_profile) != 1:
        lines.append("## 오늘 꼭 봐야 할 공고")
        if not top_items:
            lines.append("- 추천 공고가 없습니다.")
        for profile_id, item in top_items:
            job = item["job"]
            lines.append(f"- [{item['score']}] {job['company_name']} - {job['title']} ({profile_id})")
            lines.append(f"  - {job['original_url']}")
            lines.append(f"  - 이유: {' '.join(item.get('reasons', []))}")
        lines.append("")

    for profile in results_by_profile:
        heading = "오늘 꼭 봐야 할 공고" if len(results_by_profile) == 1 else f"필터: {profile.get('name') or profile.get('profile_id')}"
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
