import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.downloader import list_user_formats


class FormatListTests(unittest.TestCase):
    def test_stream_kinds_three_categories(self):
        info = {
            "formats": [
                {
                    "format_id": "18",
                    "ext": "mp4",
                    "height": 360,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "protocol": "https",
                },
                {
                    "format_id": "137",
                    "ext": "mp4",
                    "height": 1080,
                    "vcodec": "avc1",
                    "acodec": "none",
                    "protocol": "https",
                },
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "height": None,
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "protocol": "https",
                },
                {"format_id": "sb0", "vcodec": "none", "acodec": "none", "protocol": "mhtml"},
            ]
        }
        listed = list_user_formats(info)
        kinds = {f["format_id"]: f["stream_kind"] for f in listed}
        self.assertEqual(kinds["18"], "muxed")
        self.assertEqual(kinds["137"], "merge")
        self.assertEqual(kinds["140"], "audio")
        self.assertNotIn("sb0", kinds)


if __name__ == "__main__":
    unittest.main()
