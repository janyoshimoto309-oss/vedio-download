import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.captions import parse_caption_payload, pick_caption_track, transcript_plain
from services.llm import _extract_json
from services.notes import build_markdown, normalize_mind_map


VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
第一句

00:01:05.500 --> 00:01:08.000
第二句要点
"""

SRT = """1
00:00:00,000 --> 00:00:02,000
hello

2
00:00:02,000 --> 00:00:04,000
world
"""

YT_JSON3 = """{
  "events": [
    {"tStartMs": 1200, "dDurationMs": 1800, "segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
    {"tStartMs": 4000, "dDurationMs": 1000, "segs": [{"utf8": "\\n"}]}
  ]
}"""

BILI_JSON = """{
  "body": [
    {"from": 1.5, "to": 3.2, "content": "大家好"},
    {"from": 3.2, "to": 5.0, "content": "今天讲算法"}
  ]
}"""


class CaptionParseTests(unittest.TestCase):
    def test_vtt(self):
        cues = parse_caption_payload(VTT.encode(), "vtt")
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["text"], "第一句")
        self.assertAlmostEqual(cues[1]["start"], 65.5)

    def test_srt(self):
        cues = parse_caption_payload(SRT.encode(), "srt")
        self.assertEqual([c["text"] for c in cues], ["hello", "world"])

    def test_youtube_json3(self):
        cues = parse_caption_payload(YT_JSON3.encode(), "json3")
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]["text"], "Hello world")
        self.assertAlmostEqual(cues[0]["start"], 1.2)

    def test_bilibili_json(self):
        cues = parse_caption_payload(BILI_JSON.encode(), "json")
        self.assertEqual(cues[0]["text"], "大家好")
        self.assertAlmostEqual(cues[1]["start"], 3.2)

    def test_pick_prefers_zh_official(self):
        info = {
            "subtitles": {
                "en": [{"ext": "vtt", "url": "http://x/en.vtt"}],
                "zh-Hans": [{"ext": "vtt", "url": "http://x/zh.vtt"}],
            },
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "http://x/auto.vtt"}],
            },
        }
        lang, source, track = pick_caption_track(info)
        self.assertEqual(lang, "zh-Hans")
        self.assertEqual(source, "official")
        self.assertIn("zh.vtt", track["url"])

    def test_pick_auto_when_no_official(self):
        info = {
            "subtitles": {},
            "automatic_captions": {"en": [{"ext": "json3", "url": "http://x/a.json3"}]},
        }
        lang, source, track = pick_caption_track(info)
        self.assertEqual(source, "auto")
        self.assertEqual(track["ext"], "json3")

    def test_pick_skips_danmaku(self):
        info = {
            "subtitles": {
                "danmaku": [{"ext": "xml", "url": "http://x/danmaku.xml"}],
                "zh-CN": [{"ext": "json", "url": "http://x/zh.json"}],
            }
        }
        lang, source, track = pick_caption_track(info)
        self.assertEqual(lang, "zh-CN")
        self.assertIn("zh.json", track["url"])

    def test_pick_none(self):
        self.assertIsNone(pick_caption_track({"subtitles": {}, "automatic_captions": {}}))

    def test_wrapped_bilibili_json(self):
        raw = json.dumps({"code": 0, "data": {"body": [{"from": 0, "to": 1, "content": "你好"}]}})
        cues = parse_caption_payload(raw.encode(), "json")
        self.assertEqual(cues[0]["text"], "你好")

    def test_transcript_truncates(self):
        cues = [{"start": 0, "end": 1, "text": "a" * 20} for _ in range(5)]
        text = transcript_plain(cues, max_chars=40)
        self.assertIn("截断", text)


class NotesTests(unittest.TestCase):
    def test_extract_json_fence(self):
        data = _extract_json('前言\n```json\n{"overview": "x"}\n```')
        self.assertEqual(data["overview"], "x")

    def test_mind_map_normalize(self):
        tree = normalize_mind_map({"title": "根", "children": [{"label": "叶"}]})
        self.assertEqual(tree["label"], "根")
        self.assertEqual(tree["children"][0]["label"], "叶")

    def test_markdown_contains_sections(self):
        md = build_markdown(
            title="课",
            webpage_url="https://bilibili.com/video/BV1",
            overview="讲排序",
            outline=[{"timestamp": "0:01", "title": "引入", "summary": "开场"}],
            key_points=["快排平均 nlogn"],
            mind_map={"label": "算法", "children": [{"label": "排序", "children": []}]},
            cues=[{"start": 0, "end": 1, "text": "大家好"}],
            lang="zh-Hans",
            source="official",
        )
        self.assertIn("## 大纲", md)
        self.assertIn("## 核心要点", md)
        self.assertIn("## 思维导图", md)
        self.assertIn("## 字幕原文", md)
        self.assertIn("快排平均 nlogn", md)


if __name__ == "__main__":
    unittest.main()
