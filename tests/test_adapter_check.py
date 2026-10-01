import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import adapter_check  # noqa: E402

from tests.support import GatewayCase  # noqa: E402


class AdapterCheckTests(GatewayCase):
    """The requests docs/protocol.md shows a new module are requests the service really accepts."""

    def test_every_ambient_request_in_the_check_is_understood(self):
        for what, path, body, _ in adapter_check.checks():
            if path != "/ambient":
                continue
            self.provider.answers.append("Aye, keep to the main road.")
            answer = self.gateway.ambient.handle(dict(body))
            self.assertIn("text", answer, what)
            self.assertNotIn("required", str(answer.get("reason", "")), what)

    def test_a_whisper_named_by_headers_gets_the_bots_character(self):
        _, _, body, headers = adapter_check.checks()[-1]
        lowered = {key.lower(): value for key, value in headers.items()}
        status, answer = self.gateway.handle("smart", dict(body), lowered)
        self.assertEqual(status, 200)
        self.assertIn("Elorin Moonwhisper", self.system_text())


if __name__ == "__main__":
    unittest.main()
