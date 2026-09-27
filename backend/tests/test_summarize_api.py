import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from yt_dlp.utils import DownloadError

from main import app

BV = "https://www.bilibili.com/video/BV1xx411c7mD"


class SummarizeApiTests(unittest.TestCase):
    def test_download_health_unchanged(self):
        client = TestClient(app)
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("ffmpeg", data)
        self.assertNotIn("llm", data)

    def test_notes_ready(self):
        client = TestClient(app)
        res = client.get("/api/notes/ready")
        self.assertEqual(res.status_code, 200)
        self.assertIn("llm", res.json())

    def test_summarize_requires_part(self):
        client = TestClient(app)
        res = client.post("/api/notes/summarize", json={"url": BV})
        self.assertEqual(res.status_code, 422)

    def test_outline_without_key(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=False):
            res = client.post("/api/notes/summarize", json={"url": BV, "part": "outline"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("暂时不可用", res.json()["detail"])

    def test_transcript_without_key(self):
        client = TestClient(app)
        cues = [{"start": 0.0, "end": 2.0, "text": "今天讲二分查找"}]
        with patch("api.notes.llm_configured", return_value=False):
            with patch("api.notes.fetch_cues_for_url", return_value=(cues, "zh-Hans", "official", "算法课")):
                res = client.post("/api/notes/summarize", json={"url": BV, "part": "transcript"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["part"], "transcript")
        self.assertEqual(data["transcript"][0]["text"], "今天讲二分查找")
        self.assertEqual(data["outline"], [])
        self.assertIn("## 字幕原文", data["markdown"])
        self.assertNotIn("## 大纲", data["markdown"])

    def test_summarize_douyin_without_captions(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=True):
            with patch(
                "api.notes.fetch_cues_for_url",
                side_effect=DownloadError("这条视频没有字幕，暂时没法生成笔记或回答。"),
            ):
                res = client.post(
                    "/api/notes/summarize",
                    json={"url": "https://www.douyin.com/video/1234567890123456789", "part": "outline"},
                )
        self.assertEqual(res.status_code, 400)
        self.assertIn("没有字幕", res.json()["detail"])

    def test_summarize_outline_mocked(self):
        client = TestClient(app)
        cues = [{"start": 0.0, "end": 2.0, "text": "今天讲二分查找"}]
        notes = {
            "outline": [{"start": 0.0, "timestamp": "0:00", "title": "引入", "summary": "开场"}],
        }
        with patch("api.notes.llm_configured", return_value=True):
            with patch("api.notes.fetch_cues_for_url", return_value=(cues, "zh-Hans", "official", "算法课")):
                with patch("api.notes.summarize_part", return_value=notes):
                    res = client.post("/api/notes/summarize", json={"url": BV, "part": "outline"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["part"], "outline")
        self.assertEqual(data["outline"][0]["title"], "引入")
        self.assertEqual(data["key_points"], [])
        self.assertIsNone(data["mind_map"])
        self.assertIn("## 大纲", data["markdown"])
        self.assertNotIn("## 核心要点", data["markdown"])


class ChatApiTests(unittest.TestCase):
    def test_chat_without_key(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=False):
            res = client.post(
                "/api/notes/chat",
                json={"url": BV, "messages": [{"role": "user", "content": "讲了什么"}]},
            )
        self.assertEqual(res.status_code, 503)
        self.assertIn("暂时不可用", res.json()["detail"])

    def test_chat_without_captions(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=True):
            with patch(
                "api.notes.fetch_cues_for_url",
                side_effect=DownloadError("这条视频没有字幕，暂时没法生成笔记或回答。"),
            ):
                res = client.post(
                    "/api/notes/chat",
                    json={"url": BV, "messages": [{"role": "user", "content": "讲了什么"}]},
                )
        self.assertEqual(res.status_code, 400)
        self.assertIn("字幕", res.json()["detail"])

    def test_chat_uses_transcript(self):
        client = TestClient(app)
        cues = [{"start": 0.0, "end": 2.0, "text": "今天讲二分查找"}]
        captured = {}

        def fake_chat(messages):
            captured["messages"] = messages
            return "二分查找是折半。"

        with patch("api.notes.llm_configured", return_value=True):
            with patch("api.notes.fetch_cues_for_url", return_value=(cues, "zh-Hans", "official", "算法课")):
                with patch("services.notes.chat_text", fake_chat):
                    res = client.post(
                        "/api/notes/chat",
                        json={
                            "url": BV,
                            "messages": [
                                {"role": "user", "content": "这节课讲什么"},
                                {"role": "assistant", "content": "讲查找。"},
                                {"role": "user", "content": "具体怎么做"},
                            ],
                        },
                    )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "二分查找是折半。")
        system = captured["messages"][0]["content"]
        self.assertIn("今天讲二分查找", system)
        self.assertIn("算法课", system)
        self.assertEqual(captured["messages"][-1]["content"], "具体怎么做")

    def test_chat_rejects_assistant_last(self):
        client = TestClient(app)
        res = client.post(
            "/api/notes/chat",
            json={"url": BV, "messages": [{"role": "assistant", "content": "你好"}]},
        )
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
