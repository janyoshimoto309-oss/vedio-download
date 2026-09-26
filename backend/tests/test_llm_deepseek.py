import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.llm import build_chat_payload, build_text_chat_payload, chat_completions_url, redact_secret


class DeepSeekClientTests(unittest.TestCase):
    def test_official_base_without_v1(self):
        self.assertEqual(
            chat_completions_url("https://api.deepseek.com"),
            "https://api.deepseek.com/chat/completions",
        )

    def test_openai_sdk_style_v1_still_works(self):
        self.assertEqual(
            chat_completions_url("https://api.deepseek.com/v1"),
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_payload_uses_json_mode_and_disables_thinking(self):
        payload = build_chat_payload("sys json", "user")
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertIn("max_tokens", payload)
        self.assertEqual(payload["messages"][0]["role"], "system")

    def test_text_chat_payload_has_no_json_mode(self):
        payload = build_text_chat_payload([{"role": "user", "content": "问"}])
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertNotIn("response_format", payload)
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_redact_bearer_and_sk(self):
        raw = "Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz error"
        out = redact_secret(raw)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", out)
        self.assertNotIn("Bearer sk-", out)
        self.assertIn("[redacted]", out)


if __name__ == "__main__":
    unittest.main()
