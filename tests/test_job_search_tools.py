import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.mcp.server import build_server
from src.mcp.tools import jobs
from src.zighang.models import JobDetail


FIXTURES = Path(__file__).parent / "fixtures"


class JobSearchToolTests(unittest.TestCase):
    def test_search_jobs_exposes_date_filters_to_client(self):
        with patch("src.mcp.tools.jobs._client") as client_factory:
            client = client_factory.return_value
            client.search_jobs.return_value.to_dict.return_value = {"content": []}
            client.search_jobs.return_value.content = []

            result = jobs.search_jobs(
                start_date="2026-05-20T00:00:00",
                end_date="2026-05-20T23:59:59",
                sort="latest",
                size=20,
            )

        client.search_jobs.assert_called_once()
        filters = client.search_jobs.call_args.kwargs
        self.assertEqual(filters["start_date"], "2026-05-20T00:00:00")
        self.assertEqual(filters["end_date"], "2026-05-20T23:59:59")
        self.assertEqual(filters["sort"], "latest")
        self.assertEqual(filters["size"], 20)
        self.assertEqual(result["jobs"], [])

    def test_search_jobs_posted_on_builds_seoul_day_range(self):
        with patch("src.mcp.tools.jobs.search_jobs", return_value={"jobs": []}) as search_mock:
            result = jobs.search_jobs_posted_on(posted_date="2026-05-20", regions=["서울"], size=10)

        search_mock.assert_called_once()
        filters = search_mock.call_args.kwargs
        self.assertEqual(filters["start_date"], "2026-05-20T00:00:00")
        self.assertEqual(filters["end_date"], "2026-05-20T23:59:59")
        self.assertEqual(filters["sort"], "latest")
        self.assertEqual(filters["regions"], ["서울"])
        self.assertEqual(filters["size"], 10)
        self.assertEqual(result["jobs"], [])

    def test_search_pinned_jobs_uses_pinned_endpoint_filters(self):
        with patch("src.mcp.tools.jobs._client") as client_factory:
            client = client_factory.return_value
            client.search_pinned_recruitments.return_value = []

            result = jobs.search_pinned_jobs(
                keyword="Java",
                job_categories=["IT_개발"],
                start_date="2026-05-20T00:00:00",
                end_date="2026-05-20T23:59:59",
                nekara_kube=True,
            )

        client.search_pinned_recruitments.assert_called_once()
        filters = client.search_pinned_recruitments.call_args.kwargs
        self.assertEqual(filters["keyword"], "Java")
        self.assertEqual(filters["job_categories"], ["IT_개발"])
        self.assertEqual(filters["start_date"], "2026-05-20T00:00:00")
        self.assertEqual(filters["end_date"], "2026-05-20T23:59:59")
        self.assertEqual(filters["tag"], "NEKARA_KUBE")
        self.assertEqual(result["jobs"], [])

    def test_server_registers_posted_date_search_tool(self):
        server = build_server()
        tool_manager = getattr(server, "_tool_manager")

        self.assertIn("search_jobs", tool_manager._tools)
        self.assertIn("search_jobs_posted_on", tool_manager._tools)
        self.assertIn("search_pinned_jobs", tool_manager._tools)
        self.assertIn("search_latest_it_jobs", tool_manager._tools)
        self.assertIn("search_today_it_jobs", tool_manager._tools)
        self.assertIn("search_latest_jobs_for_me", tool_manager._tools)
        self.assertIn("update_user_preferences_from_text", tool_manager._tools)

    def test_recommend_jobs_limits_detail_fetches(self):
        detail_data = json.loads((FIXTURES / "job_detail.json").read_text(encoding="utf-8"))
        summary = JobDetail.from_api(detail_data).to_dict()
        second = {**summary, "id": "job-2", "title": "Summary only backend"}

        with (
            patch("src.mcp.tools.jobs.search_jobs", return_value={"jobs": [summary, second]}),
            patch("src.mcp.tools.jobs._profile_or_default", return_value={"skills": ["Spring Boot"], "keywords": [], "projects": []}),
            patch("src.mcp.tools.jobs._store") as store_factory,
            patch("src.mcp.tools.jobs._client") as client_factory,
        ):
            store = store_factory.return_value
            store.get_user_preferences.return_value = {}
            store.list_saved_jobs.return_value = []
            client = client_factory.return_value
            client.get_job_detail.return_value = JobDetail.from_api(detail_data)

            result = jobs.recommend_jobs(limit=2, max_detail_fetch=1)

        self.assertEqual(result["detail_fetch_count"], 1)
        client.get_job_detail.assert_called_once_with("job-1")
        self.assertEqual(len(result["recommendations"]), 2)
        self.assertEqual(sum(1 for item in result["recommendations"] if item["detail_fetched"]), 1)
        self.assertTrue(all("matched_signals" in item for item in result["recommendations"]))

    def test_latest_it_jobs_applies_it_category_and_internship_exclusions(self):
        with (
            patch("src.mcp.tools.jobs._preferences", return_value={"default_exclude_internships": True, "excluded_keywords": []}),
            patch("src.mcp.tools.jobs.search_jobs", return_value={"jobs": []}) as search_mock,
        ):
            result = jobs.search_latest_it_jobs(include_pinned=False)

        search_mock.assert_called_once()
        filters = search_mock.call_args.kwargs
        self.assertEqual(filters["job_categories"], ["IT_개발"])
        self.assertEqual(filters["sort"], "latest")
        self.assertIn("인턴", filters["exclude_keywords"])
        self.assertEqual(result["intent"], "latest_it_jobs")

    def test_latest_jobs_for_me_uses_stored_preferences(self):
        preferences = {
            "preferred_job_categories": ["AI_데이터"],
            "preferred_job_subcategories": ["데이터엔지니어"],
            "preferred_regions": ["서울"],
            "preferred_employment_types": ["정규직"],
            "excluded_keywords": ["인턴"],
            "default_exclude_internships": False,
        }

        with (
            patch("src.mcp.tools.jobs._preferences", return_value=preferences),
            patch("src.mcp.tools.jobs.search_jobs", return_value={"jobs": []}) as search_mock,
        ):
            result = jobs.search_latest_jobs_for_me(include_pinned=False)

        filters = search_mock.call_args.kwargs
        self.assertEqual(filters["job_categories"], ["AI_데이터"])
        self.assertEqual(filters["job_subcategories"], ["데이터엔지니어"])
        self.assertEqual(filters["regions"], ["서울"])
        self.assertEqual(filters["employment_types"], ["정규직"])
        self.assertEqual(filters["exclude_keywords"], ["인턴"])
        self.assertEqual(result["preferences"], preferences)


if __name__ == "__main__":
    unittest.main()
