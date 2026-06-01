import unittest
from unittest.mock import patch

from src.config.settings import Settings
from src.zighang.client import ZighangClient


class FilterParamTests(unittest.TestCase):
    def test_build_params_maps_public_names_to_zighang_params(self):
        client = ZighangClient(Settings(request_delay_ms=0))

        params = client.build_job_params(
            keyword="Java",
            job_categories=["IT_개발"],
            job_subcategories=["서버_백엔드"],
            regions=["서울"],
            career_min=2,
            career_max=5,
            employment_types=["정규직"],
            education_levels=["학사"],
            company_types=["대기업"],
            deadline_types=["마감일"],
            affiliates=["원티드"],
            start_date="2026-05-20T00:00:00",
            end_date="2026-05-20T23:59:59",
            tag="NEKARA_KUBE",
            include_career_open=True,
            sort="deadline",
            page=2,
            size=30,
        )

        self.assertEqual(params["depthOnes"], ["IT_개발"])
        self.assertEqual(params["depthTwos"], ["서버_백엔드"])
        self.assertEqual(params["careerMin"], 2)
        self.assertEqual(params["careerMax"], 5)
        self.assertEqual(params["employeeTypes"], ["정규직"])
        self.assertEqual(params["educations"], ["학사"])
        self.assertEqual(params["deadlineTypes"], ["마감일"])
        self.assertEqual(params["affiliates"], ["원티드"])
        self.assertEqual(params["startDate"], "2026-05-20T00:00:00")
        self.assertEqual(params["endDate"], "2026-05-20T23:59:59")
        self.assertEqual(params["tag"], "NEKARA_KUBE")
        self.assertIs(params["includeCareerOpen"], True)
        self.assertEqual(params["sortCondition"], "DEADLINE")
        self.assertEqual(params["orderCondition"], "ASC")
        self.assertEqual(params["page"], 2)
        self.assertEqual(params["size"], 30)

    def test_pinned_search_uses_site_pinned_endpoint_without_pagination_or_sort(self):
        client = ZighangClient(Settings(request_delay_ms=0))

        with patch.object(client, "_request", return_value=[]) as request_mock:
            result = client.search_pinned_recruitments(keyword="Java", sort="latest", page=2, size=30)

        request_mock.assert_called_once()
        method, path = request_mock.call_args.args[:2]
        params = request_mock.call_args.kwargs["params"]
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/recruitments/pinned")
        self.assertEqual(params["keyword"], "Java")
        self.assertNotIn("page", params)
        self.assertNotIn("size", params)
        self.assertNotIn("sortCondition", params)
        self.assertNotIn("orderCondition", params)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
