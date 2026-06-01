from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


def render_daily_digest(results_by_profile: list[dict[str, Any]], top_n: int = 5) -> str:
    all_items = []
    for profile in results_by_profile:
        for item in profile.get("recommendations", []):
            all_items.append((profile.get("profile_id"), item))
    top_items = sorted(all_items, key=lambda pair: pair[1].get("score", 0), reverse=True)[:top_n]

    lines = [f"# Zighang Daily Job Digest - {date.today().isoformat()}", ""]
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
        lines.append(f"## 필터: {profile.get('name') or profile.get('profile_id')}")
        recommendations = profile.get("recommendations", [])
        if not recommendations:
            lines.append("- 추천 공고가 없습니다.")
            continue
        for item in recommendations:
            job = item["job"]
            lines.append(f"- [{item['score']}] {job['company_name']} - {job['title']}")
            lines.append(f"  - 지역: {', '.join(job.get('regions') or []) or '-'}")
            lines.append(f"  - 마감: {job.get('deadline', {}).get('end_date') or job.get('deadline', {}).get('type') or '-'}")
            lines.append(f"  - URL: {job['original_url']}")
            if item.get("mismatches"):
                lines.append(f"  - 우려: {' '.join(item['mismatches'])}")
    lines.append("")
    return "\n".join(lines)


def save_daily_digest(markdown: str, reports_dir: Path = Path("reports/daily")) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{date.today().isoformat()}.md"
    path.write_text(markdown, encoding="utf-8")
    return path

