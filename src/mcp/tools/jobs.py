from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.config.settings import load_settings
from src.notification.channels import build_notification_channel
from src.notification.digest import render_daily_digest, save_daily_digest
from src.recommender.matcher import explain_match
from src.recommender.preference_parser import infer_preferences_from_text, merge_preferences
from src.recommender.resume_parser import analyze_text_profile, extract_projects, extract_skills, load_profile_from_paths, read_text_file
from src.recommender.scoring import deduplicate_jobs, score_job
from src.storage.db import JsonStore
from src.zighang.client import ZighangClient
from src.zighang.models import JobSummary


def _store() -> JsonStore:
    settings = load_settings()
    return JsonStore(settings.data_dir / "state.json")


def _client() -> ZighangClient:
    return ZighangClient(load_settings())


INTERNSHIP_KEYWORDS = ["인턴", "인턴십", "채용연계형", "체험형"]


def _preferences() -> dict[str, Any]:
    return _store().get_user_preferences()


def _exclude_keywords(exclude_internships: bool | None = None, extra_keywords: list[str] | None = None) -> list[str]:
    preferences = _preferences()
    keywords = list(preferences.get("excluded_keywords") or [])
    if extra_keywords:
        keywords.extend(extra_keywords)
    should_exclude_internships = preferences.get("default_exclude_internships", True) if exclude_internships is None else exclude_internships
    if should_exclude_internships:
        keywords.extend(INTERNSHIP_KEYWORDS)
    return sorted(set(keywords))


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
        "start_date": start_date,
        "end_date": end_date,
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
    if posted_date is None:
        target = datetime.now(ZoneInfo("Asia/Seoul")).date()
    else:
        target = date.fromisoformat(posted_date)

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
        start_date=f"{target.isoformat()}T00:00:00",
        end_date=f"{target.isoformat()}T23:59:59",
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
        "start_date": start_date,
        "end_date": end_date,
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
    filters = {
        "job_categories": preferences.get("preferred_job_categories") or None,
        "job_subcategories": preferences.get("preferred_job_subcategories") or None,
        "regions": preferences.get("preferred_regions") or None,
        "employment_types": preferences.get("preferred_employment_types") or None,
        "sort": "latest",
        "size": size,
        "exclude_keywords": _exclude_keywords(),
    }
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


def get_job_detail(job_id: str) -> dict[str, Any]:
    """Fetch one Zighang job posting detail by recruitment ID."""
    return _client().get_job_detail(job_id).to_dict()


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
    if preferences.get("default_exclude_internships", True):
        filters = {**filters, "exclude_keywords": _exclude_keywords()}
    page_size = max(limit, filters.get("size") or limit)
    search_result = search_jobs(**{**filters, "size": page_size})
    statuses = {item["job_id"]: item["status"] for item in store.list_saved_jobs()}
    recommendations = []
    client = _client()
    detail_fetch_count = 0
    detail_limit = len(search_result["jobs"]) if max_detail_fetch is None else max(0, max_detail_fetch)
    for item in search_result["jobs"]:
        if include_evidence and detail_fetch_count < detail_limit:
            job = client.get_job_detail(item["id"])
            detail_fetch_count += 1
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
        recommendations.append(score_job(job, resume_profile, statuses.get(item["id"]), preferences))
    recommendations.sort(key=lambda item: item["score"], reverse=True)
    return {
        "recommendations": recommendations[:limit],
        "filter": filters,
        "resume_profile_id": resume_profile_id,
        "include_evidence": include_evidence,
        "detail_fetch_count": detail_fetch_count,
        "max_detail_fetch": max_detail_fetch,
    }


def explain_job_match(job_id: str, resume_profile_id: str = "default", inline_resume: str | None = None) -> dict[str, Any]:
    store = _store()
    statuses = {item["job_id"]: item["status"] for item in store.list_saved_jobs()}
    detail = _client().get_job_detail(job_id)
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
    for profile in store.list_filter_profiles():
        if not profile.get("notifications_enabled", True):
            continue
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
        new_job_ids.extend(item["job"]["id"] for item in recommendations)
        deadline_soon_count += sum(1 for item in recommendations if _is_deadline_soon(item["job"].get("deadline", {}).get("end_date")))
        results.append({"profile_id": profile["id"], "name": profile.get("name"), "recommendations": recommendations})
    markdown = render_daily_digest(results, top_n=top_n)
    path = save_daily_digest(markdown, settings.reports_dir)
    history = store.update_digest_history(new_job_ids, datetime.now(ZoneInfo("Asia/Seoul")).isoformat())
    notification_result = build_notification_channel(settings, path).send(markdown) if send_notification else "dry-run"
    return {
        "report_path": str(path),
        "markdown": markdown,
        "profiles": results,
        "new_job_count": len(set(new_job_ids)),
        "deadline_soon_count": deadline_soon_count,
        "excluded_existing_count": excluded_existing_count,
        "digest_history": history,
        "notification_channel": settings.notification_channel,
        "notification_result": notification_result,
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
