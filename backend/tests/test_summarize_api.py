import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from main import app
from yt_dlp.utils import DownloadError


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

    def test_summarize_without_key(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=False):
            res = client.post("/api/notes/summarize", json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("DEEPSEEK_API_KEY", res.json()["detail"])

    def test_summarize_douyin_rejected(self):
        client = TestClient(app)
        with patch("api.notes.llm_configured", return_value=True):
            with patch(
                "api.notes.fetch_cues_for_url",
                side_effect=DownloadError("抖音当前没有可用字幕轨，无法生成学习笔记。请换有字幕的 B 站或 YouTube 讲解。"),
            ):
                res = client.post(
                    "/api/notes/summarize",
                    json={"url": "https://www.douyin.com/video/1234567890123456789"},
                )
        self.assertEqual(res.status_code, 400)
        self.assertIn("抖音", res.json()["detail"])

    def test_summarize_success_mocked(self):
        client = TestClient(app)
        cues = [{"start": 0.0, "end": 2.0, "text": "今天讲二分查找"}]
        notes = {
            "overview": "讲解二分",
            "outline": [{"start": 0.0, "timestamp": "0:00", "title": "引入", "summary": "开场"}],
            "key_points": ["有序数组才能二分"],
            "mind_map": {"label": "二分", "children": []},
        }
        with patch("api.notes.llm_configured", return_value=True):
            with patch("api.notes.fetch_cues_for_url", return_value=(cues, "zh-Hans", "official", "算法课")):
                with patch("api.notes.summarize_from_cues", return_value=notes):
                    res = client.post(
                        "/api/notes/summarize",
                        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
                    )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["overview"], "讲解二分")
        self.assertEqual(data["key_points"][0], "有序数组才能二分")
        self.assertIn("## 大纲", data["markdown"])
        self.assertEqual(data["transcript"][0]["text"], "今天讲二分查找")


if __name__ == "__main__":
    unittest.main()
