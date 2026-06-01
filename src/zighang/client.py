from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config.settings import Settings, load_settings
from src.zighang.filters import order_for_sort, normalize_sort, static_filter_options
from src.zighang.models import JobDetail, PaginatedJobs


class ZighangApiError(RuntimeError):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = details


class ZighangClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self._last_request = 0.0

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.settings.zighang_auth_token:
            headers["Authorization"] = f"Bearer {self.settings.zighang_auth_token}"
        if self.settings.zighang_cookie:
            headers["Cookie"] = self.settings.zighang_cookie
        return headers

    def _wait(self) -> None:
        delay = max(0, self.settings.request_delay_ms) / 1000
        if delay == 0:
            return
        elapsed = time.monotonic() - self._last_request
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        self._wait()
        query = ""
        if params:
            clean = {key: value for key, value in params.items() if value is not None and value != []}
            query = urlencode(clean, doseq=True)
        url = f"{self.settings.zighang_base_url}{path}"
        if query:
            url = f"{url}?{query}"
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urlopen(request, timeout=30) as response:
                self._last_request = time.monotonic()
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network dependent branch
            raise ZighangApiError("NETWORK_ERROR", str(exc)) from exc
        if payload.get("success") is False:
            raise ZighangApiError(payload.get("code") or "API_ERROR", payload.get("message") or "Unknown error", payload.get("data"))
        return payload.get("data")

    def build_job_params(
        self,
        *,
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
        tag: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort: str | None = None,
        page: int = 0,
        size: int | None = None,
    ) -> dict[str, Any]:
        sort_condition = normalize_sort(sort)
        return {
            "page": page,
            "size": size or self.settings.default_page_size,
            "keyword": keyword,
            "depthOnes": job_categories,
            "depthTwos": job_subcategories,
            "careerMin": career_min,
            "careerMax": career_max,
            "includeCareerOpen": include_career_open,
            "employeeTypes": employment_types,
            "regions": regions,
            "educations": education_levels,
            "companyTypes": company_types,
            "deadlineTypes": deadline_types,
            "affiliates": affiliates,
            "tag": tag,
            "startDate": start_date,
            "endDate": end_date,
            "sortCondition": sort_condition,
            "orderCondition": order_for_sort(sort_condition),
        }

    def search_jobs(self, **filters: Any) -> PaginatedJobs:
        params = self.build_job_params(**filters)
        return PaginatedJobs.from_api(self._request("GET", "/recruitments/v3", params=params))

    def search_open_recruitments(self, **filters: Any) -> PaginatedJobs:
        params = self.build_job_params(**filters)
        return PaginatedJobs.from_api(self._request("GET", "/open-recruitments", params=params))

    def search_pinned_recruitments(self, **filters: Any) -> list[JobDetail]:
        params = self.build_job_params(**filters)
        params.pop("page", None)
        params.pop("size", None)
        params.pop("sortCondition", None)
        params.pop("orderCondition", None)
        return [JobDetail.from_api(item) for item in self._request("GET", "/recruitments/pinned", params=params)]

    def get_job_detail(self, job_id: str) -> JobDetail:
        return JobDetail.from_api(self._request("GET", f"/recruitments/{job_id}"))

    def list_job_categories(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/recruitments/job-categories") or [])

    def list_filter_options(self) -> dict[str, Any]:
        options = static_filter_options()
        try:
            options["job_categories"] = self.list_job_categories()
        except ZighangApiError as exc:
            options["job_categories_error"] = {"code": exc.code, "message": exc.message}
            options["job_categories"] = []
        return options

    def list_bookmarks(self, *, page: int = 0, size: int | None = None) -> Any:
        return self._request("GET", "/bookmarks", params={"page": page, "size": size or self.settings.default_page_size})
