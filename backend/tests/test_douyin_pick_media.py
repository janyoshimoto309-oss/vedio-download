import json
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.douyin_browser import _pick_media, _urls_from_render


class DouyinPickMediaTests(unittest.TestCase):
    def test_render_prefers_matching_aweme_id(self):
        data = {
            "feed": [
                {"awemeId": "111", "src": "https://v26-web.douyinvod.com/wrong.mp4"},
                {"awemeId": "222", "src": "https://v26-web.douyinvod.com/right.mp4"},
            ]
        }
        encoded = quote(json.dumps(data, ensure_ascii=False))
        urls = _urls_from_render(encoded, "222")
        self.assertEqual(urls, ["https://v26-web.douyinvod.com/right.mp4"])

    def test_pick_media_uses_main_player_first(self):
        snapshot = {
            "mainSrc": "https://v26-web.douyinvod.com/main.mp4",
            "renderText": "",
        }
        captured = ["https://v26-web.douyinvod.com/other.mp4"]
        urls = _pick_media(captured, snapshot, "123")
        self.assertEqual(urls[0], "https://v26-web.douyinvod.com/main.mp4")


if __name__ == "__main__":
    unittest.main()
