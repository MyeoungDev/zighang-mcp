import json
import unittest
from pathlib import Path

from src.zighang.models import JobDetail, PaginatedJobs


FIXTURES = Path(__file__).parent / "fixtures"


class ModelParsingTests(unittest.TestCase):
    def test_job_list_response_parsing(self):
        data = json.loads((FIXTURES / "job_list.json").read_text(encoding="utf-8"))
        parsed = PaginatedJobs.from_api(data)

        self.assertEqual(parsed.total_elements, 1)
        self.assertEqual(parsed.content[0].company.name, "Acme")
        self.assertEqual(parsed.content[0].depth_twos, ["서버_백엔드"])
        self.assertIn("/recruitment/job-1", parsed.content[0].source_url)

    def test_job_detail_tiptap_text_parsing(self):
        data = json.loads((FIXTURES / "job_detail.json").read_text(encoding="utf-8"))
        parsed = JobDetail.from_api(data)

        self.assertIn("담당업무", parsed.summary_text)
        self.assertIn("Spring Boot API 서버 개발", parsed.summary_text)
        self.assertEqual(parsed.redirect_url, "https://example.com/apply")


if __name__ == "__main__":
    unittest.main()

