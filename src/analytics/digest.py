from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any


HIGH_SCORE_THRESHOLD = 70


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _deadline_date(job: dict[str, Any]) -> date | None:
    deadline = job.get("deadline") or {}
    end_date = deadline.get("end_date") if isinstance(deadline, dict) else None
    if not isinstance(end_date, str) or not end_date:
        return None
    try:
        return datetime.fromisoformat(end_date).date()
    except ValueError:
        return None


def _is_deadline_soon(job: dict[str, Any], today: date) -> bool:
    deadline = _deadline_date(job)
    if deadline is None:
        return False
    days = (deadline - today).days
    return 0 <= days <= 7


def _has_risk(item: dict[str, Any]) -> bool:
    return bool(item.get("risk_flags") or item.get("mismatches") or item.get("preference_warnings") or item.get("feedback_warnings"))


def _items_from_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for profile in profiles:
        profile_id = profile.get("profile_id")
        profile_name = profile.get("name")
        for item in profile.get("recommendations") or []:
            if isinstance(item, dict) and isinstance(item.get("job"), dict):
                items.append({**item, "profile_id": profile_id, "profile_name": profile_name})
    return items


def _top(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def _job_record(item: dict[str, Any]) -> dict[str, Any]:
    job = item["job"]
    return {
        "id": job.get("id"),
        "company_name": job.get("company_name"),
        "title": job.get("title"),
        "original_url": job.get("original_url"),
        "score": item.get("score", 0),
        "keywords": _as_list(job.get("keywords")),
        "jobs": _as_list(job.get("jobs")),
        "regions": _as_list(job.get("regions")),
        "deadline": job.get("deadline") or {},
        "risk_flags": _as_list(item.get("risk_flags")),
        "mismatches": _as_list(item.get("mismatches")),
        "pre_apply_tips": _as_list(item.get("pre_apply_tips")),
        "matched_signals": _as_list(item.get("matched_signals")),
        "profile_id": item.get("profile_id"),
        "profile_name": item.get("profile_name"),
    }


def build_daily_snapshot(
    snapshot_date: str,
    profiles: list[dict[str, Any]],
    report_path: str | None = None,
    source: str = "daily_job_digest",
) -> dict[str, Any]:
    today = date.fromisoformat(snapshot_date)
    items = _items_from_profiles(profiles)
    keyword_counts: Counter[str] = Counter()
    company_counts: Counter[str] = Counter()
    region_counts: Counter[str] = Counter()
    job_counts: Counter[str] = Counter()
    records = []

    for item in items:
        job = item["job"]
        records.append(_job_record(item))
        keyword_counts.update(str(value) for value in _as_list(job.get("keywords")) if value)
        company = job.get("company_name")
        if company:
            company_counts[str(company)] += 1
        region_counts.update(str(value) for value in _as_list(job.get("regions")) if value)
        job_counts.update(str(value) for value in _as_list(job.get("jobs")) if value)

    return {
        "date": snapshot_date,
        "source": source,
        "report_path": report_path,
        "total_jobs": len(records),
        "high_score_jobs": sum(1 for item in items if int(item.get("score") or 0) >= HIGH_SCORE_THRESHOLD),
        "deadline_soon": sum(1 for item in items if _is_deadline_soon(item["job"], today)),
        "risk_flagged": sum(1 for item in items if _has_risk(item)),
        "top_keywords": _top(keyword_counts),
        "top_companies": _top(company_counts),
        "top_regions": _top(region_counts),
        "top_job_categories": _top(job_counts),
        "jobs": records,
    }


def _snapshots_in_range(snapshots: list[dict[str, Any]], start_date: date, end_date: date) -> list[dict[str, Any]]:
    selected = []
    for snapshot in snapshots:
        try:
            current = date.fromisoformat(str(snapshot.get("date")))
        except ValueError:
            continue
        if start_date <= current <= end_date:
            selected.append(snapshot)
    return selected


def _collect_snapshot_stats(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    jobs_by_id: dict[str, dict[str, Any]] = {}
    keyword_counts: Counter[str] = Counter()
    company_counts: Counter[str] = Counter()
    region_counts: Counter[str] = Counter()
    job_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    deadline_soon = 0
    high_score_ids: set[str] = set()

    for snapshot in snapshots:
        for record in snapshot.get("jobs") or []:
            job_id = str(record.get("id") or "")
            if not job_id:
                continue
            previous = jobs_by_id.get(job_id)
            if previous is None or int(record.get("score") or 0) > int(previous.get("score") or 0):
                jobs_by_id[job_id] = record
            if int(record.get("score") or 0) >= HIGH_SCORE_THRESHOLD:
                high_score_ids.add(job_id)
            keyword_counts.update(str(value) for value in _as_list(record.get("keywords")) if value)
            company = record.get("company_name")
            if company:
                company_counts[str(company)] += 1
            region_counts.update(str(value) for value in _as_list(record.get("regions")) if value)
            job_counts.update(str(value) for value in _as_list(record.get("jobs")) if value)
            risk_counts.update(str(value) for value in _as_list(record.get("risk_flags")) if value)
            gap_counts.update(str(value) for value in [*_as_list(record.get("mismatches")), *_as_list(record.get("pre_apply_tips"))] if value)
            if _is_deadline_soon(record, date.today()):
                deadline_soon += 1

    top_jobs = sorted(jobs_by_id.values(), key=lambda record: int(record.get("score") or 0), reverse=True)[:10]
    return {
        "total_jobs": len(jobs_by_id),
        "high_score_jobs": len(high_score_ids),
        "deadline_soon": deadline_soon,
        "top_keywords": _top(keyword_counts),
        "top_companies": _top(company_counts),
        "top_regions": _top(region_counts),
        "top_job_categories": _top(job_counts),
        "top_risks": _top(risk_counts),
        "top_gap_signals": _top(gap_counts),
        "representative_jobs": top_jobs,
    }


def build_weekly_summary(
    snapshots: list[dict[str, Any]],
    week_start_date: str,
    end_date: str,
) -> dict[str, Any]:
    start = date.fromisoformat(week_start_date)
    end = date.fromisoformat(end_date)
    selected = _snapshots_in_range(snapshots, start, end)
    stats = _collect_snapshot_stats(selected)
    return {
        "week_start_date": week_start_date,
        "end_date": end_date,
        "insufficient_data": not selected,
        "snapshot_count": len(selected),
        **stats,
    }


def compare_market_trends(
    recent_snapshots: list[dict[str, Any]],
    previous_snapshots: list[dict[str, Any]],
    days: int,
) -> dict[str, Any]:
    recent = _collect_snapshot_stats(recent_snapshots)
    previous = _collect_snapshot_stats(previous_snapshots)

    def changed(field: str) -> list[dict[str, Any]]:
        recent_counts = {item["value"]: item["count"] for item in recent[field]}
        previous_counts = {item["value"]: item["count"] for item in previous[field]}
        values = sorted(set(recent_counts) | set(previous_counts))
        rows = [
            {
                "value": value,
                "recent_count": recent_counts.get(value, 0),
                "previous_count": previous_counts.get(value, 0),
                "delta": recent_counts.get(value, 0) - previous_counts.get(value, 0),
            }
            for value in values
        ]
        rows.sort(key=lambda row: (abs(row["delta"]), row["recent_count"]), reverse=True)
        return rows[:10]

    repeated_companies = [
        item for item in recent["top_companies"] if item["count"] >= 2
    ]
    return {
        "days": days,
        "insufficient_data": not recent_snapshots,
        "comparison_available": bool(previous_snapshots),
        "recent": recent,
        "previous": previous if previous_snapshots else None,
        "keyword_changes": changed("top_keywords") if previous_snapshots else [],
        "company_changes": changed("top_companies") if previous_snapshots else [],
        "region_changes": changed("top_regions") if previous_snapshots else [],
        "job_category_changes": changed("top_job_categories") if previous_snapshots else [],
        "repeated_companies": repeated_companies,
    }


def build_resume_gap_analysis(
    snapshots: list[dict[str, Any]],
    days: int,
    resume_profile_id: str,
) -> dict[str, Any]:
    stats = _collect_snapshot_stats(snapshots)
    return {
        "days": days,
        "resume_profile_id": resume_profile_id,
        "insufficient_data": not snapshots,
        "analyzed_jobs": stats["total_jobs"],
        "top_gap_signals": stats["top_gap_signals"],
        "top_risks": stats["top_risks"],
        "resume_gap_keywords": stats["top_keywords"],
        "representative_jobs": stats["representative_jobs"],
    }


def period_for_last_days(today: date, days: int) -> tuple[date, date, date, date]:
    recent_end = today
    recent_start = today - timedelta(days=max(1, days) - 1)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=max(1, days) - 1)
    return recent_start, recent_end, previous_start, previous_end
