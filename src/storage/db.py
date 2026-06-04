from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_STATE = {
    "filter_profiles": {},
    "job_statuses": {},
    "resume_profiles": {},
    "job_detail_cache": {},
    "daily_snapshots": {},
    "job_history": {},
    "weekly_summaries": {},
    "seen_jobs": {},
    "user_preferences": {
        "preferred_job_categories": [],
        "preferred_job_subcategories": [],
        "preferred_regions": [],
        "preferred_employment_types": [],
        "excluded_keywords": [],
        "excluded_company_names": [],
        "preferred_keywords": [],
        "preferred_skills": [],
        "disliked_keywords": [],
        "default_exclude_internships": True,
    },
    "digest_history": {
        "last_run_at": None,
        "seen_job_ids": [],
    },
}


@dataclass
class JsonStore:
    path: Path = Path("data/cache/state.json")

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return deepcopy(DEFAULT_STATE)
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        state = deepcopy(DEFAULT_STATE)
        state.update(data)
        for key, default_value in DEFAULT_STATE.items():
            if isinstance(default_value, dict) and isinstance(state.get(key), dict):
                state[key] = {**deepcopy(default_value), **state[key]}
        return state

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(self.path)

    def upsert_filter_profile(self, profile_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["filter_profiles"][profile_id] = {"id": profile_id, **profile}
        self.save(state)
        return state["filter_profiles"][profile_id]

    def list_filter_profiles(self) -> list[dict[str, Any]]:
        return list(self.load()["filter_profiles"].values())

    def get_filter_profile(self, profile_id: str) -> dict[str, Any] | None:
        return self.load()["filter_profiles"].get(profile_id)

    def delete_filter_profile(self, profile_id: str) -> bool:
        state = self.load()
        existed = profile_id in state["filter_profiles"]
        state["filter_profiles"].pop(profile_id, None)
        self.save(state)
        return existed

    def mark_job_status(self, job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
        state = self.load()
        record = {"job_id": job_id, "status": status, "notes": notes}
        state["job_statuses"][job_id] = record
        state["seen_jobs"][job_id] = True
        self.save(state)
        return record

    def list_saved_jobs(self, statuses: list[str] | None = None) -> list[dict[str, Any]]:
        jobs = list(self.load()["job_statuses"].values())
        if statuses:
            jobs = [job for job in jobs if job.get("status") in statuses]
        return jobs

    def track_job_status(self, job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
        return self.mark_job_status(job_id, status, notes)

    def list_tracked_jobs(self, statuses: list[str] | None = None) -> list[dict[str, Any]]:
        return self.list_saved_jobs(statuses)

    def save_resume_profile(self, profile_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["resume_profiles"][profile_id] = {"id": profile_id, **profile}
        self.save(state)
        return state["resume_profiles"][profile_id]

    def get_resume_profile(self, profile_id: str = "default") -> dict[str, Any] | None:
        return self.load()["resume_profiles"].get(profile_id)

    def get_job_detail_cache(self, job_id: str) -> dict[str, Any] | None:
        return self.load()["job_detail_cache"].get(job_id)

    def upsert_job_detail_cache(self, job_id: str, detail: dict[str, Any], fetched_at: str, max_entries: int = 500) -> dict[str, Any]:
        state = self.load()
        cache = state["job_detail_cache"]
        cache[job_id] = {
            "job_id": job_id,
            "detail": detail,
            "fetched_at": fetched_at,
            "source": "zighang",
        }
        if max_entries > 0 and len(cache) > max_entries:
            overflow = len(cache) - max_entries
            for old_key, _ in sorted(cache.items(), key=lambda pair: str(pair[1].get("fetched_at") or ""))[:overflow]:
                cache.pop(old_key, None)
        self.save(state)
        return cache[job_id]

    def get_user_preferences(self) -> dict[str, Any]:
        return self.load()["user_preferences"]

    def update_user_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        updated = {**state["user_preferences"], **preferences}
        state["user_preferences"] = updated
        self.save(state)
        return updated

    def clear_user_preferences(self) -> dict[str, Any]:
        state = self.load()
        state["user_preferences"] = deepcopy(DEFAULT_STATE["user_preferences"])
        self.save(state)
        return state["user_preferences"]

    def update_digest_history(self, seen_job_ids: list[str], last_run_at: str) -> dict[str, Any]:
        state = self.load()
        existing = set(state.get("digest_history", {}).get("seen_job_ids") or [])
        existing.update(seen_job_ids)
        state["digest_history"] = {
            "last_run_at": last_run_at,
            "seen_job_ids": sorted(existing),
        }
        self.save(state)
        return state["digest_history"]

    def upsert_daily_snapshot(self, snapshot_date: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["daily_snapshots"][snapshot_date] = snapshot
        self.save(state)
        return snapshot

    def upsert_job_history_from_snapshot(self, snapshot_date: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        history = state["job_history"]
        for record in snapshot.get("jobs") or []:
            job_id = str(record.get("id") or "")
            if not job_id:
                continue
            previous = history.get(job_id, {})
            score = int(record.get("score") or 0)
            history[job_id] = {
                "id": job_id,
                "company_name": record.get("company_name"),
                "title": record.get("title"),
                "original_url": record.get("original_url"),
                "first_seen_date": previous.get("first_seen_date") or snapshot_date,
                "last_seen_date": snapshot_date,
                "seen_count": int(previous.get("seen_count") or 0) + 1,
                "best_score": max(int(previous.get("best_score") or 0), score),
                "latest_score": score,
                "keywords": record.get("keywords") or [],
                "jobs": record.get("jobs") or [],
                "regions": record.get("regions") or [],
                "deadline": record.get("deadline") or {},
                "risk_flags": record.get("risk_flags") or [],
                "mismatches": record.get("mismatches") or [],
                "pre_apply_tips": record.get("pre_apply_tips") or [],
                "matched_signals": record.get("matched_signals") or [],
            }
        self.save(state)
        return history

    def save_digest_snapshot(self, snapshot_date: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        self.upsert_daily_snapshot(snapshot_date, snapshot)
        self.upsert_job_history_from_snapshot(snapshot_date, snapshot)
        return snapshot

    def list_daily_snapshots(self, start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
        snapshots = list(self.load()["daily_snapshots"].values())
        if start_date is not None:
            snapshots = [item for item in snapshots if str(item.get("date") or "") >= start_date]
        if end_date is not None:
            snapshots = [item for item in snapshots if str(item.get("date") or "") <= end_date]
        return sorted(snapshots, key=lambda item: str(item.get("date") or ""))

    def save_weekly_summary(self, week_id: str, summary: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["weekly_summaries"][week_id] = summary
        self.save(state)
        return summary
