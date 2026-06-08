from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.analytics.digest import (
    build_daily_snapshot,
    build_resume_gap_analysis,
    build_weekly_summary,
    compare_market_trends,
    period_for_last_days,
)
from src.config.settings import load_settings
from src.notification.channels import build_notification_channel
from src.notification.digest import render_daily_digest, render_digest_setup_required, save_daily_digest
from src.recommender.matcher import explain_match
from src.recommender.preference_parser import infer_preferences_from_text, merge_preferences
from src.recommender.resume_parser import analyze_text_profile, extract_projects, extract_skills, load_profile_from_paths, read_text_file
from src.recommender.scoring import deduplicate_jobs, score_job
from src.storage.db import JsonStore
from src.zighang.client import ZighangClient
from src.zighang.models import Company, JobDetail, JobSummary


def _store() -> JsonStore:
    settings = load_settings()
    return JsonStore(settings.data_dir / "state.json")


def _client() -> ZighangClient:
    return ZighangClient(load_settings())


INTERNSHIP_KEYWORDS = ["인턴", "인턴십", "채용연계형", "체험형"]
FEEDBACK_STATUSES = {"interested", "bookmarked", "applied", "ignored", "rejected"}


def _now_seoul() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul"))


def _today_seoul() -> date:
    return _now_seoul().date()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return parsed


def _cache_age_hours(fetched_at: str | None) -> float | None:
    parsed = _parse_datetime(fetched_at)
    if parsed is None:
        return None
    return max(0.0, (_now_seoul() - parsed).total_seconds() / 3600)


def _job_detail_from_dict(data: dict[str, Any]) -> JobDetail:
    deadline = data.get("deadline") or {}
    career = data.get("career") or {}
    return JobDetail(
        id=str(data.get("id", "")),
        affiliate=data.get("affiliate"),
        company=Company(id="", name=str(data.get("company_name", ""))),
        title=str(data.get("title", "")),
        end_date=deadline.get("end_date"),
        deadline_type=deadline.get("type"),
        career_min=career.get("min"),
        career_max=career.get("max"),
        regions=list(data.get("regions") or []),
        employee_types=list(data.get("employment_types") or []),
        educations=list(data.get("education_levels") or []),
        depth_twos=list(data.get("jobs") or []),
        keywords=list(data.get("keywords") or []),
        summary_text=str(data.get("detail") or ""),
        content_text=str(data.get("content") or ""),
        redirect_url=data.get("redirect_url"),
        status=data.get("status"),
        pinned=bool(data.get("pinned")),
    )


def _cache_meta(record: dict[str, Any] | None, hit: bool, ttl_hours: int) -> dict[str, Any]:
    fetched_at = record.get("fetched_at") if record else None
    return {
        "cache_hit": hit,
        "cache_fetched_at": fetched_at,
        "cache_age_hours": _cache_age_hours(fetched_at),
        "cache_ttl_hours": ttl_hours,
    }


def _get_job_detail_cached(job_id: str, refresh: bool = False) -> tuple[JobDetail, dict[str, Any]]:
    settings = load_settings()
    store = JsonStore(settings.data_dir / "state.json")
    ttl_hours = settings.job_detail_cache_ttl_hours
    record = store.get_job_detail_cache(job_id)
    if not refresh and record and isinstance(record.get("detail"), dict):
        age = _cache_age_hours(record.get("fetched_at"))
        if age is not None and age <= ttl_hours:
            try:
                return _job_detail_from_dict(record["detail"]), _cache_meta(record, True, ttl_hours)
            except Exception:
                pass

    detail = _client().get_job_detail(job_id)
    fetched_at = _now_seoul().isoformat()
    record = store.upsert_job_detail_cache(
        job_id,
        detail.to_dict(),
        fetched_at,
        max_entries=settings.job_detail_cache_max_entries,
    )
    return detail, _cache_meta(record, False, ttl_hours)


def _cached_feedback_jobs(store: JsonStore) -> list[dict[str, Any]]:
    feedback = []
    for item in store.list_saved_jobs():
        status = item.get("status")
        job_id = item.get("job_id")
        if status not in FEEDBACK_STATUSES or not job_id:
            continue
        record = store.get_job_detail_cache(job_id)
        detail = record.get("detail") if record else None
        if not isinstance(detail, dict):
            continue
        try:
            feedback.append({"status": status, "job": _job_detail_from_dict(detail)})
        except Exception:
            continue
    return feedback


def _preferences() -> dict[str, Any]:
    return _store().get_user_preferences()


def _exclude_keywords(exclude_internships: bool | None = None, extra_keywords: list[str] | None = None) -> list[str]:
    preferences = _preferences()
    return _exclude_keywords_from_preferences(preferences, exclude_internships, extra_keywords)


def _exclude_keywords_from_preferences(
    preferences: dict[str, Any],
    exclude_internships: bool | None = None,
    extra_keywords: list[str] | None = None,
) -> list[str]:
    keywords = list(preferences.get("excluded_keywords") or [])
    if extra_keywords:
        keywords.extend(extra_keywords)
    should_exclude_internships = preferences.get("default_exclude_internships", True) if exclude_internships is None else exclude_internships
    if should_exclude_internships:
        keywords.extend(INTERNSHIP_KEYWORDS)
    return sorted(set(keywords))


def _coerce_local_datetime(value: str | None, boundary: str) -> str | None:
    if not value:
        return None
    try:
        if "T" not in value:
            parsed_date = date.fromisoformat(value)
            suffix = "00:00:00" if boundary == "start" else "23:59:59"
            return f"{parsed_date.isoformat()}T{suffix}"
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{boundary}_date must be YYYY-MM-DD or ISO LocalDateTime: {value}") from exc
    return parsed.replace(tzinfo=None).isoformat(timespec="seconds")


def _posted_date_range(posted_date: str | None = None) -> tuple[str, str, str]:
    target = datetime.now(ZoneInfo("Asia/Seoul")).date() if posted_date is None else date.fromisoformat(posted_date)
    day = target.isoformat()
    return day, f"{day}T00:00:00", f"{day}T23:59:59"


def _digest_date_range(lookback_hours: int = 24) -> tuple[str, str, str]:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if lookback_hours <= 0:
        day = now.date().isoformat()
        return day, f"{day}T00:00:00", f"{day}T23:59:59"
    start = now - timedelta(hours=lookback_hours)
    return now.date().isoformat(), start.replace(tzinfo=None).isoformat(timespec="seconds"), now.replace(tzinfo=None).isoformat(timespec="seconds")


def _filters_from_preferences(preferences: dict[str, Any], size: int | None = None, sort: str | None = "latest") -> dict[str, Any]:
    filters: dict[str, Any] = {
        "job_categories": preferences.get("preferred_job_categories") or None,
        "job_subcategories": preferences.get("preferred_job_subcategories") or None,
        "regions": preferences.get("preferred_regions") or None,
        "employment_types": preferences.get("preferred_employment_types") or None,
        "sort": sort,
        "exclude_keywords": _exclude_keywords_from_preferences(preferences),
    }
    if size is not None:
        filters["size"] = size
    return filters


def _job_has_excluded_company(job: Any, preferences: dict[str, Any]) -> bool:
    excluded = [str(item).lower() for item in preferences.get("excluded_company_names") or []]
    return any(company and company in job.company.name.lower() for company in excluded)


def _filter_jobs_by_preferences(jobs: list[Any], preferences: dict[str, Any]) -> list[Any]:
    return [job for job in jobs if not _job_has_excluded_company(job, preferences)]


def _profile_or_default(resume_profile_id: str = "default", inline_resume: str | None = None) -> dict[str, Any]:
    if inline_resume:
        return analyze_text_profile(inline_resume, "inline")
    store = _store()
    profile = store.get_resume_profile(resume_profile_id)
    if profile:
        return profile
    settings = load_settings()
    loaded = load_profile_from_paths(settings.resume_path, settings.portfolio_path)
    return store.save_resume_profile(resume_profile_id, loaded)


def search_jobs(
    keyword: str | None = None,
    job_categories: list[str] | None = None,
    job_subcategories: list[str] | None = None,
    regions: list[str] | None = None,
    career_min: int | None = None,
    career_max: int | None = None,
    include_career_open: bool | None = None,
    employment_types: list[str] | None = None,
    education_levels: list[str] | None = None,
    company_types: list[str] | None = None,
    deadline_types: list[str] | None = None,
    affiliates: list[str] | None = None,
    sort: str | None = "recommended",
    page: int = 0,
    size: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    open_recruitments: bool = False,
    nekara_kube: bool = False,
    exclude_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Low-level Zighang public job search with explicit filters.

    Use this when the user provides concrete keyword/filter parameters. For
    "나에게 맞는 공고" or resume/profile-based recommendations, prefer
    recommend_jobs. For stored preference based latest jobs, prefer
    search_latest_jobs_for_me. For "오늘 올라온" prompts, prefer
    search_jobs_posted_on or search_today_it_jobs.
    """
    client = _client()
    filters = {
        "keyword": keyword,
        "job_categories": job_categories,
        "job_subcategories": job_subcategories,
        "regions": regions,
        "career_min": career_min,
        "career_max": career_max,
        "include_career_open": include_career_open,
        "employment_types": employment_types,
        "education_levels": education_levels,
        "company_types": company_types,
        "deadline_types": deadline_types,
        "affiliates": affiliates,
        "sort": sort,
        "page": page,
        "size": size,
        "start_date": _coerce_local_datetime(start_date, "start"),
        "end_date": _coerce_local_datetime(end_date, "end"),
        "tag": "NEKARA_KUBE" if nekara_kube else None,
    }
    result = client.search_open_recruitments(**filters) if open_recruitments else client.search_jobs(**filters)
    jobs = deduplicate_jobs(result.content)
    if exclude_keywords:
        lowered = [item.lower() for item in exclude_keywords]
        jobs = [job for job in jobs if not any(token in (job.title + " " + job.company.name + " " + " ".join(job.keywords)).lower() for token in lowered)]
    jobs = _filter_jobs_by_preferences(jobs, _preferences())
    data = result.to_dict()
    data["jobs"] = [job.to_dict() for job in jobs]
    data["deduplicated_count"] = len(jobs)
    return data


def search_jobs_posted_on(
    posted_date: str | None = None,
    keyword: str | None = None,
    job_categories: list[str] | None = None,
    job_subcategories: list[str] | None = None,
    regions: list[str] | None = None,
    career_min: int | None = None,
    career_max: int | None = None,
    include_career_open: bool | None = None,
    employment_types: list[str] | None = None,
    education_levels: list[str] | None = None,
    company_types: list[str] | None = None,
    deadline_types: list[str] | None = None,
    affiliates: list[str] | None = None,
    page: int = 0,
    size: int | None = None,
    open_recruitments: bool = False,
    nekara_kube: bool = False,
    exclude_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Search Zighang jobs posted on a specific Asia/Seoul calendar date.

    Use this tool first for Korean prompts such as "직행에 오늘 올라온 공고",
    "오늘 등록된 IT 공고", or "오늘 최신공고". The default posted_date is
    today's date in Asia/Seoul.
    """
    _, start_date, end_date = _posted_date_range(posted_date)

    return search_jobs(
        keyword=keyword,
        job_categories=job_categories,
        job_subcategories=job_subcategories,
        regions=regions,
        career_min=career_min,
        career_max=career_max,
        include_career_open=include_career_open,
        employment_types=employment_types,
        education_levels=education_levels,
        company_types=company_types,
        deadline_types=deadline_types,
        affiliates=affiliates,
        sort="latest",
        page=page,
        size=size,
        start_date=start_date,
        end_date=end_date,
        open_recruitments=open_recruitments,
        nekara_kube=nekara_kube,
        exclude_keywords=exclude_keywords,
    )


def search_pinned_jobs(
    keyword: str | None = None,
    job_categories: list[str] | None = None,
    job_subcategories: list[str] | None = None,
    regions: list[str] | None = None,
    career_min: int | None = None,
    career_max: int | None = None,
    employment_types: list[str] | None = None,
    education_levels: list[str] | None = None,
    company_types: list[str] | None = None,
    deadline_types: list[str] | None = None,
    affiliates: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    nekara_kube: bool = False,
    exclude_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Search Zighang pinned recruitment postings.

    Use this with search_jobs when matching the live Zighang recruitment page,
    because the site requests pinned jobs alongside the normal latest list.
    """
    filters = {
        "keyword": keyword,
        "job_categories": job_categories,
        "job_subcategories": job_subcategories,
        "regions": regions,
        "career_min": career_min,
        "career_max": career_max,
        "employment_types": employment_types,
        "education_levels": education_levels,
        "company_types": company_types,
        "deadline_types": deadline_types,
        "affiliates": affiliates,
        "start_date": _coerce_local_datetime(start_date, "start"),
        "end_date": _coerce_local_datetime(end_date, "end"),
        "tag": "NEKARA_KUBE" if nekara_kube else None,
    }
    pinned = _client().search_pinned_recruitments(**filters)
    jobs = deduplicate_jobs(pinned)
    if exclude_keywords:
        lowered = [item.lower() for item in exclude_keywords]
        jobs = [job for job in jobs if not any(token in (job.title + " " + job.company.name + " " + " ".join(job.keywords)).lower() for token in lowered)]
    return {"jobs": [job.to_dict() for job in jobs], "deduplicated_count": len(jobs), "filter": filters}


def _merge_search_results(primary: dict[str, Any], pinned: dict[str, Any]) -> dict[str, Any]:
    seen = set()
    merged = []
    for job in pinned.get("jobs", []) + primary.get("jobs", []):
        key = (job.get("company_name", "").strip().lower(), job.get("title", "").strip().lower(), job.get("affiliate"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(job)
    result = dict(primary)
    result["jobs"] = merged
    result["deduplicated_count"] = len(merged)
    result["pinned_count"] = len(pinned.get("jobs", []))
    return result


def _pinned_filters(filters: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "keyword",
        "job_categories",
        "job_subcategories",
        "regions",
        "career_min",
        "career_max",
        "employment_types",
        "education_levels",
        "company_types",
        "deadline_types",
        "affiliates",
        "start_date",
        "end_date",
        "nekara_kube",
        "exclude_keywords",
    }
    return {key: value for key, value in filters.items() if key in allowed}


def _is_deadline_soon(end_date: str | None) -> bool:
    if not end_date:
        return False
    try:
        days = (datetime.fromisoformat(end_date).date() - datetime.now(ZoneInfo("Asia/Seoul")).date()).days
    except ValueError:
        return False
    return 0 <= days <= 7


def _record_digest_snapshot(
    store: JsonStore,
    snapshot_date: str,
    profiles: list[dict[str, Any]],
    report_path: str | None,
    source: str,
) -> dict[str, Any]:
    snapshot = build_daily_snapshot(
        snapshot_date=snapshot_date,
        profiles=profiles,
        report_path=report_path,
        source=source,
    )
    return store.save_digest_snapshot(snapshot_date, snapshot)


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def search_latest_it_jobs(size: int = 10, include_pinned: bool = True, exclude_internships: bool | None = None) -> dict[str, Any]:
    """Search latest Zighang IT_개발 jobs when the user asks for broad latest IT postings.

    Use this for prompts like "직행 최신공고 IT 직군" when personalization is
    not requested. For "나에게 맞는" latest jobs, prefer search_latest_jobs_for_me
    or recommend_jobs.
    """
    excluded = _exclude_keywords(exclude_internships)
    result = search_jobs(job_categories=["IT_개발"], sort="latest", size=size, exclude_keywords=excluded)
    if include_pinned:
        pinned = search_pinned_jobs(job_categories=["IT_개발"], exclude_keywords=excluded)
        result = _merge_search_results(result, pinned)
    result["intent"] = "latest_it_jobs"
    return result


def search_today_it_jobs(size: int = 10, include_pinned: bool = True, exclude_internships: bool | None = None) -> dict[str, Any]:
    """Search today's Zighang IT_개발 jobs using Asia/Seoul date.

    Use this first for prompts like "오늘 올라온 IT 공고" or "오늘 등록된
    개발 공고". For arbitrary dates, use search_jobs_posted_on.
    """
    excluded = _exclude_keywords(exclude_internships)
    today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    result = search_jobs_posted_on(posted_date=today, job_categories=["IT_개발"], size=size, exclude_keywords=excluded)
    if include_pinned:
        pinned = search_pinned_jobs(
            job_categories=["IT_개발"],
            start_date=f"{today}T00:00:00",
            end_date=f"{today}T23:59:59",
            exclude_keywords=excluded,
        )
        result = _merge_search_results(result, pinned)
    result["intent"] = "today_it_jobs"
    return result


def search_latest_jobs_for_me(size: int = 10, include_pinned: bool = True) -> dict[str, Any]:
    """Search latest Zighang jobs using stored local user preferences.

    Use this for "내 조건/선호도 기준 최신 공고" prompts. If the user asks for
    resume/profile-based ranking or "왜 맞는지" reasoning, prefer recommend_jobs.
    """
    preferences = _preferences()
    filters = _filters_from_preferences(preferences, size=size, sort="latest")
    result = search_jobs(**filters)
    if include_pinned:
        pinned = search_pinned_jobs(
            job_categories=filters["job_categories"],
            job_subcategories=filters["job_subcategories"],
            regions=filters["regions"],
            employment_types=filters["employment_types"],
            exclude_keywords=filters["exclude_keywords"],
        )
        result = _merge_search_results(result, pinned)
    result["intent"] = "latest_jobs_for_me"
    result["preferences"] = preferences
    return result


def search_today_jobs_for_me(size: int = 10, include_pinned: bool = True) -> dict[str, Any]:
    """Search today's Zighang jobs using stored local user preferences.

    Use this for prompts like "내 조건으로 오늘 올라온 공고" or "직행 오늘자
    내 공고". For a rendered report, prefer daily_job_digest_for_me.
    """
    preferences = _preferences()
    posted_date, start_date, end_date = _posted_date_range()
    filters = _filters_from_preferences(preferences, size=size, sort="latest")
    result = search_jobs_posted_on(
        posted_date=posted_date,
        job_categories=filters["job_categories"],
        job_subcategories=filters["job_subcategories"],
        regions=filters["regions"],
        employment_types=filters["employment_types"],
        size=size,
        exclude_keywords=filters["exclude_keywords"],
    )
    if include_pinned:
        pinned = search_pinned_jobs(
            job_categories=filters["job_categories"],
            job_subcategories=filters["job_subcategories"],
            regions=filters["regions"],
            employment_types=filters["employment_types"],
            start_date=start_date,
            end_date=end_date,
            exclude_keywords=filters["exclude_keywords"],
        )
        result = _merge_search_results(result, pinned)
    result["intent"] = "today_jobs_for_me"
    result["posted_date"] = posted_date
    result["preferences"] = preferences
    result["applied_filters"] = {**filters, "start_date": start_date, "end_date": end_date}
    return result


def get_job_detail(job_id: str, refresh: bool = False) -> dict[str, Any]:
    """Fetch one Zighang job posting detail by recruitment ID, using the local detail cache by default."""
    detail, cache = _get_job_detail_cached(job_id, refresh=refresh)
    data = detail.to_dict()
    data["cache"] = cache
    return data


def list_filter_options() -> dict[str, Any]:
    """List Zighang job filter options such as IT_개발, regions, company types, and affiliates."""
    return _client().list_filter_options()


def recommend_jobs(
    filter_profile_id: str | None = None,
    inline_filter: dict[str, Any] | None = None,
    resume_profile_id: str = "default",
    inline_resume: str | None = None,
    limit: int = 10,
    include_evidence: bool = True,
    max_detail_fetch: int | None = None,
) -> dict[str, Any]:
    """Recommend and rank jobs using resume/profile data plus stored preferences.

    Use this as the default tool for prompts like "나에게 맞는 공고", "내 이력
    기준 추천", or "이를 토대로 직행 MCP로 맞는 공고". Avoid replacing this
    with many ad-hoc search_jobs keyword calls unless the user explicitly asks
    for manual keyword exploration.
    """
    store = _store()
    filters = inline_filter or {}
    if filter_profile_id:
        profile = store.get_filter_profile(filter_profile_id)
        if not profile:
            raise ValueError(f"Unknown filter profile: {filter_profile_id}")
        filters = profile.get("filters") or {}
    resume_profile = _profile_or_default(resume_profile_id, inline_resume)
    preferences = store.get_user_preferences()
    feedback_jobs = _cached_feedback_jobs(store)
    if preferences.get("default_exclude_internships", True):
        filters = {**filters, "exclude_keywords": _exclude_keywords()}
    page_size = max(limit, filters.get("size") or limit)
    search_result = search_jobs(**{**filters, "size": page_size})
    statuses = {item["job_id"]: item["status"] for item in store.list_saved_jobs()}
    recommendations = []
    detail_fetch_count = 0
    cache_hit_count = 0
    detail_limit = len(search_result["jobs"]) if max_detail_fetch is None else max(0, max_detail_fetch)
    for item in search_result["jobs"]:
        cache = None
        if include_evidence and detail_fetch_count < detail_limit:
            job, cache = _get_job_detail_cached(item["id"])
            detail_fetch_count += 1
            if cache["cache_hit"]:
                cache_hit_count += 1
        else:
            job = JobSummary.from_api(
                {
                    "id": item.get("id"),
                    "affiliate": item.get("affiliate"),
                    "company": {"id": "", "name": item.get("company_name", "")},
                    "title": item.get("title", ""),
                    "endDate": (item.get("deadline") or {}).get("end_date"),
                    "deadlineType": (item.get("deadline") or {}).get("type"),
                    "careerMin": (item.get("career") or {}).get("min"),
                    "careerMax": (item.get("career") or {}).get("max"),
                    "regions": item.get("regions") or [],
                    "employeeTypes": item.get("employment_types") or [],
                    "educations": item.get("education_levels") or [],
                    "depthOnes": [],
                    "depthTwos": item.get("jobs") or [],
                    "depthThrees": [],
                    "keywords": item.get("keywords") or [],
                    "tags": [],
                    "badges": [],
                }
            )
        scored = score_job(job, resume_profile, statuses.get(item["id"]), preferences, feedback_jobs=feedback_jobs)
        if cache:
            scored["cache"] = cache
        recommendations.append(scored)
    recommendations.sort(key=lambda item: item["score"], reverse=True)
    return {
        "recommendations": recommendations[:limit],
        "filter": filters,
        "resume_profile_id": resume_profile_id,
        "include_evidence": include_evidence,
        "detail_fetch_count": detail_fetch_count,
        "cache_hit_count": cache_hit_count,
        "max_detail_fetch": max_detail_fetch,
    }


def explain_job_match(job_id: str, resume_profile_id: str = "default", inline_resume: str | None = None) -> dict[str, Any]:
    store = _store()
    statuses = {item["job_id"]: item["status"] for item in store.list_saved_jobs()}
    detail, _ = _get_job_detail_cached(job_id)
    return explain_match(detail, _profile_or_default(resume_profile_id, inline_resume), statuses.get(job_id), store.get_user_preferences())


def save_filter_profile(profile_id: str, name: str, filters: dict[str, Any], notifications_enabled: bool = True) -> dict[str, Any]:
    return _store().upsert_filter_profile(
        profile_id,
        {"name": name, "filters": filters, "notifications_enabled": notifications_enabled},
    )


def list_filter_profiles() -> list[dict[str, Any]]:
    return _store().list_filter_profiles()


def update_filter_profile(profile_id: str, name: str | None = None, filters: dict[str, Any] | None = None, notifications_enabled: bool | None = None) -> dict[str, Any]:
    store = _store()
    existing = store.get_filter_profile(profile_id)
    if not existing:
        raise ValueError(f"Unknown filter profile: {profile_id}")
    updated = dict(existing)
    if name is not None:
        updated["name"] = name
    if filters is not None:
        updated["filters"] = filters
    if notifications_enabled is not None:
        updated["notifications_enabled"] = notifications_enabled
    return store.upsert_filter_profile(profile_id, updated)


def delete_filter_profile(profile_id: str) -> dict[str, Any]:
    return {"profile_id": profile_id, "deleted": _store().delete_filter_profile(profile_id)}


def daily_job_digest(
    resume_profile_id: str = "default",
    limit_per_profile: int = 5,
    top_n: int = 5,
    exclude_seen: bool = True,
    send_notification: bool = True,
    only_new: bool = True,
    include_tracked: bool = False,
    include_pinned: bool = True,
) -> dict[str, Any]:
    store = _store()
    settings = load_settings()
    state = store.load()
    results = []
    seen = set(state.get("seen_jobs", {}).keys()) if exclude_seen else set()
    tracked = set(state.get("job_statuses", {}).keys()) if not include_tracked else set()
    digest_seen = set(state.get("digest_history", {}).get("seen_job_ids") or []) if only_new else set()
    excluded = seen | tracked | digest_seen
    new_job_ids = []
    excluded_existing_count = 0
    deadline_soon_count = 0
    feedback_boosted_count = 0
    risk_flagged_count = 0
    active_profiles = [profile for profile in store.list_filter_profiles() if profile.get("notifications_enabled", True)]
    if not active_profiles:
        markdown = render_digest_setup_required()
        path = save_daily_digest(markdown, settings.reports_dir)
        notification_result = build_notification_channel(settings, path).send(markdown) if send_notification else "dry-run"
        return {
            "report_path": str(path),
            "markdown": markdown,
            "profiles": [],
            "new_job_count": 0,
            "deadline_soon_count": 0,
            "excluded_existing_count": 0,
            "feedback_boosted_count": 0,
            "risk_flagged_count": 0,
            "digest_history": state.get("digest_history", {}),
            "notification_channel": settings.notification_channel,
            "notification_result": notification_result,
            "setup_required": True,
            "setup_message": "No active filter profiles. Call save_filter_profile before daily_job_digest.",
        }

    for profile in active_profiles:
        profile_filters = profile.get("filters") or {}
        rec = recommend_jobs(filter_profile_id=profile["id"], resume_profile_id=resume_profile_id, limit=limit_per_profile * 2)
        recommendations = []
        if include_pinned:
            pinned = search_pinned_jobs(**_pinned_filters(profile_filters))
            for job in pinned.get("jobs", []):
                if job["id"] in excluded:
                    excluded_existing_count += 1
                    continue
                recommendations.append({"score": 40, "job": job, "reasons": ["직행 고정 공고입니다."], "mismatches": [], "preference_reasons": [], "preference_warnings": []})
        for item in rec["recommendations"]:
            job_id = item["job"]["id"]
            if job_id in excluded:
                excluded_existing_count += 1
                continue
            recommendations.append(item)
        recommendations = recommendations[:limit_per_profile]
        feedback_boosted_count += sum(1 for item in recommendations if item.get("feedback_reasons") or (item.get("score_breakdown") or {}).get("feedback_affinity", 0) > 0)
        risk_flagged_count += sum(1 for item in recommendations if item.get("risk_flags") or item.get("mismatches") or item.get("feedback_warnings"))
        new_job_ids.extend(item["job"]["id"] for item in recommendations)
        deadline_soon_count += sum(1 for item in recommendations if _is_deadline_soon(item["job"].get("deadline", {}).get("end_date")))
        results.append({"profile_id": profile["id"], "name": profile.get("name"), "recommendations": recommendations})
    markdown = render_daily_digest(results, top_n=top_n)
    path = save_daily_digest(markdown, settings.reports_dir)
    snapshot_date = _today_seoul().isoformat()
    snapshot = _record_digest_snapshot(store, snapshot_date, results, str(path), "daily_job_digest")
    notification_result = build_notification_channel(settings, path).send(markdown) if send_notification else "dry-run"
    history = (
        store.update_digest_history(new_job_ids, datetime.now(ZoneInfo("Asia/Seoul")).isoformat())
        if send_notification
        else state.get("digest_history", {})
    )
    return {
        "report_path": str(path),
        "markdown": markdown,
        "profiles": results,
        "new_job_count": len(set(new_job_ids)),
        "deadline_soon_count": deadline_soon_count,
        "excluded_existing_count": excluded_existing_count,
        "feedback_boosted_count": feedback_boosted_count,
        "risk_flagged_count": risk_flagged_count,
        "digest_history": history,
        "snapshot_date": snapshot["date"],
        "notification_channel": settings.notification_channel,
        "notification_result": notification_result,
        "setup_required": False,
    }


def daily_job_digest_for_me(
    resume_profile_id: str = "default",
    limit: int = 10,
    top_n: int = 5,
    exclude_seen: bool = True,
    send_notification: bool = False,
    only_new: bool = True,
    include_tracked: bool = False,
    include_pinned: bool = True,
    max_detail_fetch: int | None = None,
    save_report: bool = True,
    lookback_hours: int = 24,
) -> dict[str, Any]:
    """Generate a digest from stored user preferences without requiring filter profiles.

    Use this as the default for prompts such as "직행 오늘자 보고서" or
    "내 조건 기준 오늘 올라온 공고 보고서". By default it looks back 24
    hours so morning reports include postings from the previous afternoon.
    """
    store = _store()
    settings = load_settings()
    state = store.load()
    preferences = store.get_user_preferences()
    posted_date, start_date, end_date = _digest_date_range(lookback_hours)
    filters = {**_filters_from_preferences(preferences, size=max(limit * 2, limit), sort="latest"), "start_date": start_date, "end_date": end_date}
    seen = set(state.get("seen_jobs", {}).keys()) if exclude_seen else set()
    tracked = set(state.get("job_statuses", {}).keys()) if not include_tracked else set()
    digest_seen = set(state.get("digest_history", {}).get("seen_job_ids") or []) if only_new else set()
    excluded = seen | tracked | digest_seen
    recommendations = []
    excluded_existing_count = 0

    if include_pinned:
        pinned = search_pinned_jobs(**_pinned_filters(filters))
        for job in pinned.get("jobs", []):
            if job["id"] in excluded:
                excluded_existing_count += 1
                continue
            recommendations.append(
                {
                    "score": 40,
                    "job": job,
                    "reasons": ["직행 고정 공고입니다."],
                    "mismatches": [],
                    "preference_reasons": [],
                    "preference_warnings": [],
                }
            )

    rec = recommend_jobs(
        inline_filter=filters,
        resume_profile_id=resume_profile_id,
        limit=limit * 2,
        max_detail_fetch=max_detail_fetch,
    )
    for item in rec["recommendations"]:
        job_id = item["job"]["id"]
        if job_id in excluded:
            excluded_existing_count += 1
            continue
        recommendations.append(item)

    recommendations = sorted(recommendations, key=lambda item: item.get("score", 0), reverse=True)[:limit]
    profile_result = {"profile_id": "user_preferences", "name": "저장된 선호조건", "recommendations": recommendations}
    markdown = render_daily_digest([profile_result], top_n=top_n)
    path = save_daily_digest(markdown, settings.reports_dir) if save_report or send_notification else None
    snapshot = None
    if path:
        snapshot = _record_digest_snapshot(store, posted_date, [profile_result], str(path), "daily_job_digest_for_me")
    notification_result = build_notification_channel(settings, path).send(markdown) if send_notification and path else "dry-run"
    new_job_ids = [item["job"]["id"] for item in recommendations]
    history = (
        store.update_digest_history(new_job_ids, datetime.now(ZoneInfo("Asia/Seoul")).isoformat())
        if send_notification
        else state.get("digest_history", {})
    )
    return {
        "report_path": str(path) if path else None,
        "markdown": markdown,
        "profiles": [profile_result],
        "new_job_count": len(set(new_job_ids)),
        "deadline_soon_count": sum(1 for item in recommendations if _is_deadline_soon(item["job"].get("deadline", {}).get("end_date"))),
        "excluded_existing_count": excluded_existing_count,
        "feedback_boosted_count": sum(1 for item in recommendations if item.get("feedback_reasons") or (item.get("score_breakdown") or {}).get("feedback_affinity", 0) > 0),
        "risk_flagged_count": sum(1 for item in recommendations if item.get("risk_flags") or item.get("mismatches") or item.get("feedback_warnings")),
        "digest_history": history,
        "snapshot_date": snapshot["date"] if snapshot else None,
        "notification_channel": settings.notification_channel,
        "notification_result": notification_result,
        "setup_required": False,
        "posted_date": posted_date,
        "lookback_hours": lookback_hours,
        "preferences": preferences,
        "applied_filters": filters,
        "recommendation_meta": {
            "include_evidence": rec.get("include_evidence"),
            "detail_fetch_count": rec.get("detail_fetch_count"),
            "cache_hit_count": rec.get("cache_hit_count"),
            "max_detail_fetch": rec.get("max_detail_fetch"),
        },
    }


def get_digest_history(days: int = 7) -> dict[str, Any]:
    """Return recent structured daily digest snapshots for Agent analysis."""
    safe_days = max(1, days)
    today = _today_seoul()
    start = today - timedelta(days=safe_days - 1)
    snapshots = _store().list_daily_snapshots(start.isoformat(), today.isoformat())
    return {
        "days": safe_days,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "insufficient_data": not snapshots,
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
    }


def get_weekly_job_summary(week_start_date: str | None = None) -> dict[str, Any]:
    """Summarize this week's structured digest history for Agent reporting."""
    today = _today_seoul()
    start = date.fromisoformat(week_start_date) if week_start_date else _week_start(today)
    store = _store()
    snapshots = store.list_daily_snapshots(start.isoformat(), today.isoformat())
    summary = build_weekly_summary(snapshots, start.isoformat(), today.isoformat())
    week_id = f"{start.isoformat()}_{today.isoformat()}"
    return store.save_weekly_summary(week_id, summary)


def get_job_market_trends(days: int = 7) -> dict[str, Any]:
    """Compare recent digest keyword/company/region/job trends with the previous period."""
    safe_days = max(1, days)
    today = _today_seoul()
    recent_start, recent_end, previous_start, previous_end = period_for_last_days(today, safe_days)
    store = _store()
    recent = store.list_daily_snapshots(recent_start.isoformat(), recent_end.isoformat())
    previous = store.list_daily_snapshots(previous_start.isoformat(), previous_end.isoformat())
    result = compare_market_trends(recent, previous, safe_days)
    return {
        **result,
        "recent_period": {"start_date": recent_start.isoformat(), "end_date": recent_end.isoformat()},
        "previous_period": {"start_date": previous_start.isoformat(), "end_date": previous_end.isoformat()},
    }


def get_resume_gap_analysis(days: int = 7, resume_profile_id: str = "default") -> dict[str, Any]:
    """Aggregate repeated risk and resume-gap signals from recent digest history."""
    safe_days = max(1, days)
    today = _today_seoul()
    start = today - timedelta(days=safe_days - 1)
    snapshots = _store().list_daily_snapshots(start.isoformat(), today.isoformat())
    result = build_resume_gap_analysis(snapshots, safe_days, resume_profile_id)
    return {
        **result,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
    }


def track_job_status(job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
    """Track a job status in local MCP state, not in the Zighang account."""
    allowed = {"new", "viewed", "bookmarked", "interested", "applied", "rejected", "ignored"}
    if status not in allowed:
        raise ValueError(f"Unsupported status: {status}")
    return _store().track_job_status(job_id, status, notes)


def mark_job_status(job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
    """Backward-compatible alias for track_job_status."""
    return track_job_status(job_id, status, notes)


def list_tracked_jobs(statuses: list[str] | None = None) -> list[dict[str, Any]]:
    """List locally tracked jobs. This does not read Zighang account bookmarks."""
    return _store().list_tracked_jobs(statuses)


def list_saved_jobs(statuses: list[str] | None = None) -> list[dict[str, Any]]:
    """Deprecated compatibility alias for list_tracked_jobs.

    This returns MCP-local tracked jobs, not Zighang account bookmarks.
    Prefer list_tracked_jobs in new Agent calls.
    """
    return list_tracked_jobs(statuses)


def get_user_preferences() -> dict[str, Any]:
    """Return local user preferences used by search and recommendation tools."""
    return _store().get_user_preferences()


def update_user_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    """Update local user preferences used by search and recommendation tools."""
    return _store().update_user_preferences(preferences)




def update_user_preferences_from_text(text: str, merge: bool = True) -> dict[str, Any]:
    """Infer and save local user preferences from natural language.

    Use this when the user says preferences such as "백엔드/데이터 플랫폼
    위주, 서울 정규직, 인턴 제외". This is rules-based and stores structured
    preferences for search_latest_jobs_for_me and recommend_jobs.
    """
    store = _store()
    parsed = infer_preferences_from_text(text)
    updated = merge_preferences(store.get_user_preferences(), parsed["extracted"], merge=merge)
    saved = store.update_user_preferences(updated)
    return {
        "preferences": saved,
        "extracted": parsed["extracted"],
        "unmatched_terms": parsed["unmatched_terms"],
        "merge": merge,
    }


def clear_user_preferences() -> dict[str, Any]:
    """Reset local user preferences to defaults."""
    return _store().clear_user_preferences()


def load_resume_profile(profile_id: str = "default", resume_path: str | None = None, portfolio_path: str | None = None) -> dict[str, Any]:
    settings = load_settings()
    profile = load_profile_from_paths(resume_path or settings.resume_path, portfolio_path or settings.portfolio_path)
    return _store().save_resume_profile(profile_id, profile)


def update_resume_profile(profile_id: str = "default", text: str | None = None, path: str | None = None) -> dict[str, Any]:
    if text is None and path is None:
        raise ValueError("Either text or path is required")
    profile = analyze_text_profile(text if text is not None else read_text_file(Path(path or "")), path or "inline")
    return _store().save_resume_profile(profile_id, profile)


def analyze_resume_profile(profile_id: str = "default", text: str | None = None) -> dict[str, Any]:
    return _profile_or_default(profile_id, text)


def extract_skills_from_resume(text: str | None = None, path: str | None = None) -> dict[str, Any]:
    source_text = text if text is not None else read_text_file(Path(path or load_settings().resume_path))
    return {"skills": extract_skills(source_text)}


def extract_projects_from_portfolio(text: str | None = None, path: str | None = None) -> dict[str, Any]:
    source_text = text if text is not None else read_text_file(Path(path or load_settings().portfolio_path))
    return {"projects": extract_projects(source_text)}
