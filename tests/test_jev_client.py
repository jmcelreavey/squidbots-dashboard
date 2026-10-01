import os
import unittest
from unittest import mock

from mind import jev
from tests.support import StubProvider


class SelfHostedJevTests(unittest.TestCase):
    """A Jev-compatible service of your own (JEV_URL) needs no key and costs nothing."""

    def setUp(self):
        self.provider = StubProvider()
        self.addCleanup(self.provider.close)
        jev.BREAKER.failures, jev.BREAKER.open_until = 0, 0.0
        jev.STATS.update({"calls": 0, "failures": 0, "input_tokens": 0})

    def environment(self, **values):
        base = {"JEV_API_KEY": "", "JEV_KEY_FILE": "", "JEV_URL": "", "JEV_MODEL": ""}
        return mock.patch.dict(os.environ, dict(base, **values))

    def test_without_a_key_or_a_url_jev_is_not_available(self):
        with self.environment():
            self.assertFalse(jev.available())
            with self.assertRaises(jev.JevError):
                jev.decide({}, {})

    def test_a_url_of_your_own_is_available_without_a_key_and_sends_no_authorization(self):
        self.provider.answers.append({"answers": {"pick": {"choice": "1", "probabilities": {"1": 0.9}}}, "usage": {"input_tokens": 700}})
        with self.environment(JEV_URL=self.provider.url + "/systemone", JEV_MODEL="tev1:4b"):
            self.assertTrue(jev.available())
            answers = jev.decide({"chat": ["hi"]}, {"pick": jev.choice_question("which?", {"1": "a", "0": "none"})})
            self.assertEqual(jev.top_choice(answers["pick"], ["1", "0"]), ("1", 0.9))
            self.assertEqual(jev.price_per_m_input(), 0.0)
            self.assertEqual(jev.spent_usd(), 0.0)
        sent = self.provider.requests[-1]
        self.assertEqual(sent["path"], "/v1/systemone")
        self.assertEqual(sent["body"]["model"], "tev1:4b")
        self.assertNotIn("Authorization", sent["headers"])

    def test_the_hosted_service_still_costs_and_still_wants_its_key(self):
        with self.environment(JEV_API_KEY="k"):
            self.assertTrue(jev.available())
            self.assertGreater(jev.price_per_m_input(), 0)
            self.assertEqual(jev.endpoint(), jev.ENDPOINT)
            self.assertEqual(jev.model_name(), jev.MODEL)


if __name__ == "__main__":
    unittest.main()
