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
        self.assertIn("DEEPSEEK_API_KEY", res.json()["detail"])

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
                side_effect=DownloadError(
                    "这个抖音视频没有可下载的字幕轨（画面上烧进去的字不算）。"
                    "第一期不做语音转写。请换油管带 CC / 自动字幕的讲解。"
                ),
            ):
                res = client.post(
                    "/api/notes/summarize",
                    json={"url": "https://www.douyin.com/video/1234567890123456789", "part": "outline"},
                )
        self.assertEqual(res.status_code, 400)
        self.assertIn("抖音", res.json()["detail"])

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


if __name__ == "__main__":
    unittest.main()
