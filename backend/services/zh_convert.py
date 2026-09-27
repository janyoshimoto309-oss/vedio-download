from __future__ import annotations

from functools import lru_cache
from typing import Any

from services.captions import Cue


@lru_cache(maxsize=1)
def _converter():
    from opencc import OpenCC

    return OpenCC("t2s")


def to_simplified(text: str) -> str:
    if not text:
        return text
    return _converter().convert(text)


def simplify_outline(outline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in outline:
        out.append(
            {
                **item,
                "title": to_simplified(str(item.get("title") or "")),
                "summary": to_simplified(str(item.get("summary") or "")),
            }
        )
    return out


def simplify_key_points(points: list[str]) -> list[str]:
    return [to_simplified(p) for p in points]


def simplify_mind_map(node: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {"label": "视频内容", "children": []}
    children = node.get("children") or []
    return {
        "label": to_simplified(str(node.get("label") or "节点")),
        "children": [simplify_mind_map(c) for c in children if isinstance(c, dict)],
    }


def simplify_cues(cues: list[Cue]) -> list[Cue]:
    out: list[Cue] = []
    for c in cues:
        out.append({**c, "text": to_simplified(str(c.get("text") or ""))})
    return out
