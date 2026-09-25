import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.url_normalize import extract_video_url, is_douyin_url


class UrlNormalizeTests(unittest.TestCase):
    def test_is_douyin_only_douyin_hosts(self):
        self.assertTrue(is_douyin_url("https://www.douyin.com/video/1"))
        self.assertTrue(is_douyin_url("https://v.douyin.com/abc/"))
        self.assertFalse(is_douyin_url("https://www.bilibili.com/video/BV1xx"))
        self.assertFalse(is_douyin_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_douyin_url("https://www.youtube.com/watch?v=abc&ref=douyin.com"))

    def test_plain_url(self):
        url = "https://www.douyin.com/video/123"
        self.assertEqual(extract_video_url(url), url)

    def test_share_text(self):
        raw = "6.6 复制打开抖音，看看https://v.douyin.com/iJxAbcDe/ 长按复制此条消息"
        self.assertEqual(extract_video_url(raw), "https://v.douyin.com/iJxAbcDe/")

    def test_modal_id_preferred(self):
        raw = "搜索页 https://www.douyin.com/search/foo?modal_id=7511391905553337619"
        self.assertEqual(extract_video_url(raw), "https://www.douyin.com/video/7511391905553337619")

    def test_user_page_modal(self):
        raw = (
            "https://www.douyin.com/user/MS4wLjABAAAA3QWZsa5ZEr-DdVn7g3JPo53xPm0oqa48rDg0dMZLSh2kdByWz_Ze7E5_6wEbsCp1"
            "?from_tab_name=main&modal_id=7681616967740808435&vid=7674189093626716018"
        )
        self.assertEqual(extract_video_url(raw), "https://www.douyin.com/video/7681616967740808435")

    def test_trailing_punctuation(self):
        raw = "see https://v.douyin.com/abc123/."
        self.assertEqual(extract_video_url(raw), "https://v.douyin.com/abc123/")


if __name__ == "__main__":
    unittest.main()
