import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.download_strategy import choose_mode, skip_redownload_info_probe
from services.proxy_token import issue, verify


class StrategyTests(unittest.TestCase):
    def test_skip_redownload_for_bilibili_auto(self):
        self.assertTrue(skip_redownload_info_probe("https://www.bilibili.com/video/BV1xx", "auto"))

    def test_skip_redownload_for_youtube_auto(self):
        self.assertTrue(skip_redownload_info_probe("https://www.youtube.com/watch?v=abc", "auto"))

    def test_skip_redownload_not_for_douyin(self):
        self.assertFalse(skip_redownload_info_probe("https://www.douyin.com/video/1", "auto"))

    def test_skip_redownload_false_for_direct(self):
        self.assertFalse(skip_redownload_info_probe("https://www.bilibili.com/video/BV1xx", "direct"))

    def test_fragment_uses_server(self):
        mode, reason = choose_mode({}, {"protocol": "m3u8", "url": "https://x/a.m3u8"}, "auto")
        self.assertEqual(mode, "server")
        self.assertIn("分片", reason)

    def test_video_only_uses_server(self):
        mode, _ = choose_mode({}, {"vcodec": "avc1", "acodec": "none", "url": "https://x/v.mp4"}, "auto")
        self.assertEqual(mode, "server")

    def test_youtube_prefers_server(self):
        mode, _ = choose_mode(
            {"extractor": "youtube"},
            {"protocol": "https", "url": "https://x/v.mp4", "vcodec": "avc1", "acodec": "mp4a"},
            "auto",
        )
        self.assertEqual(mode, "server")

    def test_progressive_redirect(self):
        mode, _ = choose_mode(
            {"extractor": "generic"},
            {"protocol": "https", "url": "https://cdn.example/v.mp4", "vcodec": "avc1", "acodec": "mp4a"},
            "auto",
        )
        self.assertEqual(mode, "redirect")

    def test_prefer_server(self):
        mode, _ = choose_mode(
            {"extractor": "generic"},
            {"protocol": "https", "url": "https://cdn.example/v.mp4", "vcodec": "avc1", "acodec": "mp4a"},
            "server",
        )
        self.assertEqual(mode, "server")

    def test_no_url_server(self):
        mode, _ = choose_mode({}, {"protocol": "https", "vcodec": "avc1", "acodec": "mp4a"}, "auto")
        self.assertEqual(mode, "server")

    def test_referer_uses_proxy(self):
        mode, _ = choose_mode(
            {"extractor": "generic"},
            {
                "protocol": "https",
                "url": "https://cdn.example/v.mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "http_headers": {"Referer": "https://example.com"},
            },
            "auto",
        )
        self.assertEqual(mode, "proxy")


class TokenTests(unittest.TestCase):
    def test_roundtrip(self):
        token = issue("https://cdn.example/a.mp4", {"Referer": "https://x"}, "a.mp4")
        data = verify(token)
        self.assertEqual(data["u"], "https://cdn.example/a.mp4")
        self.assertEqual(data["h"]["Referer"], "https://x")


if __name__ == "__main__":
    unittest.main()
