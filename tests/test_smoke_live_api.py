import os
import unittest

from src.config.settings import Settings
from src.zighang.client import ZighangClient


@unittest.skipUnless(os.getenv("RUN_LIVE_API_TESTS") == "1", "live API smoke tests are opt-in")
class LiveApiSmokeTests(unittest.TestCase):
    def test_live_search(self):
        client = ZighangClient(Settings(request_delay_ms=300))
        result = client.search_jobs(keyword="Java", size=1, sort="latest")
        self.assertGreaterEqual(result.total_elements, 0)


if __name__ == "__main__":
    unittest.main()

