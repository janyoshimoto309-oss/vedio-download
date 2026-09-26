from __future__ import annotations

from typing import Any, Literal

from services.captions import Cue, format_timestamp, transcript_plain
from services.llm import chat_json

NotePart = Literal["outline", "points", "map", "transcript"]

RULES = """你是学习向的视频课代表。根据带时间戳的字幕写笔记。
要求：
- 全部使用简体中文。不要编造字幕里没有的事实。
- outline 按时间顺序，start_seconds 必须能对上字幕时间；章节不宜过碎，长视频 6 到 16 章。
- mind_map 两到三层，label 简短。
必须输出 json 对象（不要 Markdown 围栏）。"""

PART_JSON = {
    "outline": '{"outline": [{"start_seconds": 0, "title": "章节标题", "summary": "该段核心内容"}]}',
    "points": '{"key_points": ["可独立理解的知识要点，8到15条"]}',
    "map": '{"mind_map": {"label": "中心主题", "children": [{"label": "分支", "children": [{"label": "叶子"}]}]}}',
}


def normalize_mind_map(node: Any) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {"label": "视频内容", "children": []}
    label = str(node.get("label") or node.get("title") or node.get("name") or "节点").strip()
    raw_children = node.get("children") or []
    children = [normalize_mind_map(c) for c in raw_children if c] if isinstance(raw_children, list) else []
    return {"label": label or "节点", "children": children}


def parse_outline(raw: dict[str, Any]) -> list[dict[str, Any]]:
    outline = []
    for item in raw.get("outline") or []:
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start_seconds") if item.get("start_seconds") is not None else item.get("start") or 0)
        except (TypeError, ValueError):
            start = 0.0
        heading = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if heading:
            outline.append(
                {
                    "start": start,
                    "timestamp": format_timestamp(start),
                    "title": heading,
                    "summary": summary,
                }
            )
    return outline


def parse_key_points(raw: dict[str, Any]) -> list[str]:
    return [str(p).strip() for p in (raw.get("key_points") or []) if str(p).strip()]


def summarize_part(part: NotePart, title: str, transcript: str) -> dict[str, Any]:
    system = f"{RULES}\n字段示例：{PART_JSON[part]}"
    user = f"视频标题：{title}\n\n字幕：\n{transcript}"
    raw = chat_json(system, user)
    if part == "outline":
        return {"outline": parse_outline(raw)}
    if part == "points":
        return {"key_points": parse_key_points(raw)}
    return {"mind_map": normalize_mind_map(raw.get("mind_map"))}


def build_markdown(
    title: str,
    webpage_url: str,
    language: str,
    source: str,
    *,
    outline: list[dict[str, Any]] | None = None,
    key_points: list[str] | None = None,
    mind_map: dict[str, Any] | None = None,
    cues: list[Cue] | None = None,
    overview: str | None = None,
) -> str:
    src_label = "官方字幕" if source == "official" else "自动字幕"
    lines = [
        f"# {title}",
        "",
        f"来源：{webpage_url}",
        f"字幕：{language}（{src_label}）",
        "",
    ]
    if overview:
        lines.extend(["## 总览", "", overview, ""])
    if outline is not None:
        lines.extend(["## 大纲", ""])
        if outline:
            for item in outline:
                lines.append(f"- **[{item.get('timestamp')}] {item.get('title')}** — {item.get('summary') or ''}".rstrip(" —"))
        else:
            lines.append("（无）")
        lines.append("")
    if key_points is not None:
        lines.extend(["## 核心要点", ""])
        if key_points:
            for i, p in enumerate(key_points, 1):
                lines.append(f"{i}. {p}")
        else:
            lines.append("（无）")
        lines.append("")
    if mind_map is not None:
        lines.extend(["## 思维导图", ""])
        lines.extend(_mind_map_md(mind_map, 0))
        lines.append("")
    if cues is not None:
        lines.extend(["## 字幕原文", ""])
        lines.append(transcript_plain(cues, 200_000))
        lines.append("")
    return "\n".join(lines)


def _mind_map_md(node: dict[str, Any], depth: int) -> list[str]:
    indent = "  " * depth
    rows = [f"{indent}- {node.get('label') or '节点'}"]
    for child in node.get("children") or []:
        rows.extend(_mind_map_md(child, depth + 1))
    return rows
