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
            lines.append(f"  - 지역: {', '.join(job.get('regions') or []) or '-'}")
            lines.append(f"  - 마감: {_format_deadline(job.get('deadline'))}")
            lines.append(f"  - URL: {job['original_url']}")
            if item.get("reasons"):
                lines.append(f"  - 이유: {' '.join(item['reasons'])}")
            if item.get("mismatches"):
                lines.append(f"  - 우려: {' '.join(item['mismatches'])}")
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
