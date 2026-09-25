import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.downloader import VideoDownloader, build_ydl_opts


class PlatformIsolationTests(unittest.TestCase):
    def test_bilibili_ydl_opts_have_no_cookie_or_impersonate(self):
        opts = build_ydl_opts("https://www.bilibili.com/video/BV1xx", skip_download=True)
        self.assertNotIn("cookiefile", opts)
        self.assertNotIn("cookiesfrombrowser", opts)
        self.assertNotIn("impersonate", opts)

    def test_youtube_ydl_opts_have_no_cookie_or_impersonate(self):
        opts = build_ydl_opts("https://www.youtube.com/watch?v=dQw4w9WgXcQ", skip_download=True)
        self.assertNotIn("cookiefile", opts)
        self.assertNotIn("cookiesfrombrowser", opts)
        self.assertNotIn("impersonate", opts)

    def test_get_info_does_not_open_browser_for_bilibili(self):
        fake = {
            "title": "bili",
            "extractor": "BiliBili",
            "extractor_key": "BiliBili",
            "formats": [{"format_id": "1", "url": "https://cdn.example/v.mp4", "ext": "mp4"}],
        }

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                return fake

            def sanitize_info(self, info):
                return info

        downloader = VideoDownloader()
        downloader._info_cache = {}
        with patch("services.downloader.extract_douyin_in_browser") as browser:
            with patch("services.downloader.YoutubeDL", FakeYDL):
                info = downloader.get_info("https://www.bilibili.com/video/BV1xx411c7mD")
        browser.assert_not_called()
        self.assertEqual(info["extractor"], "BiliBili")

    def test_get_info_does_not_open_browser_for_youtube(self):
        fake = {
            "title": "yt",
            "extractor": "youtube",
            "extractor_key": "Youtube",
            "formats": [{"format_id": "1", "url": "https://cdn.example/v.mp4", "ext": "mp4"}],
        }

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                return fake

            def sanitize_info(self, info):
                return info

        downloader = VideoDownloader()
        downloader._info_cache = {}
        with patch("services.downloader.extract_douyin_in_browser") as browser:
            with patch("services.downloader.YoutubeDL", FakeYDL):
                info = downloader.get_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        browser.assert_not_called()
        self.assertEqual(info["extractor"], "youtube")

    def test_douyin_get_info_uses_browser_once(self):
        payload = {
            "title": "dy",
            "extractor": "DouyinBrowser",
            "formats": [{"format_id": "browser-0", "url": "https://v26-web.douyinvod.com/a.mp4", "ext": "mp4"}],
        }
        downloader = VideoDownloader()
        downloader._info_cache = {}
        with patch("services.downloader.extract_douyin_in_browser", return_value=payload) as browser:
            first = downloader.get_info("https://www.douyin.com/video/123")
            second = downloader.get_info("https://www.douyin.com/video/123")
        self.assertEqual(browser.call_count, 1)
        self.assertEqual(first["extractor"], "DouyinBrowser")
        self.assertEqual(second["extractor"], "DouyinBrowser")


if __name__ == "__main__":
    unittest.main()
