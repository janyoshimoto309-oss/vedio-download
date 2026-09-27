import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.zh_convert import simplify_cues, simplify_key_points, to_simplified


class ZhConvertTests(unittest.TestCase):
    def test_traditional_to_simplified(self):
        self.assertEqual(to_simplified("繁體中文與發佈"), "繁体中文与发布")

    def test_already_simplified_unchanged(self):
        self.assertEqual(to_simplified("简体中文"), "简体中文")

    def test_cues_text(self):
        cues = [{"start": 0.0, "end": 1.0, "text": "這是測試"}]
        out = simplify_cues(cues)
        self.assertEqual(out[0]["text"], "这是测试")

    def test_key_points(self):
        self.assertEqual(simplify_key_points(["導輯與製作"]), ["导辑与制作"])


if __name__ == "__main__":
    unittest.main()
