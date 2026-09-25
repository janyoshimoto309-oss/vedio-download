from __future__ import annotations

import json
import re
from typing import Any

import httpx
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from services.downloader import build_ydl_opts
from services.url_normalize import is_douyin_url

LANG_PREF = (
    "zh-hans",
    "zh-cn",
    "zh",
    "zh-hant",
    "zh-tw",
    "zh-hk",
    "en",
    "en-us",
    "en-gb",
)

SKIP_LANGS = {"danmaku", "live_chat", "danmaku-ai"}
EXT_PREF = ("json3", "json", "srv3", "vtt", "srt", "ttml")

Cue = dict[str, Any]


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _norm_lang(code: str) -> str:
    return str(code or "").strip().lower().replace("_", "-")


def pick_caption_track(info: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    tracks = list(iter_caption_tracks(info))
    return tracks[0] if tracks else None


def iter_caption_tracks(info: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Prefer zh/en speech tracks; skip danmaku. Order: official then auto, by lang pref, then formats."""
    found: list[tuple[str, str, dict[str, Any]]] = []
    seen: set[str] = set()
    for source, bucket in (("official", info.get("subtitles") or {}), ("auto", info.get("automatic_captions") or {})):
        if not isinstance(bucket, dict) or not bucket:
            continue
        langs = _ordered_langs(list(bucket.keys()))
        for lang in langs:
            formats = bucket.get(lang) or []
            if not isinstance(formats, list):
                continue
            for fmt in _ordered_formats(formats):
                url = str(fmt.get("url") or "")
                if not url or url in seen:
                    continue
                seen.add(url)
                found.append((str(lang), source, fmt))
    return found


def _ordered_langs(keys: list[str]) -> list[str]:
    usable = [k for k in keys if _norm_lang(k) not in SKIP_LANGS]
    ranked: list[str] = []
    rest: list[str] = []
    by_norm = {_norm_lang(k): k for k in usable}
    used: set[str] = set()
    for pref in LANG_PREF:
        orig = by_norm.get(pref)
        if orig and orig not in used:
            ranked.append(orig)
            used.add(orig)
            continue
        for nk, orig in by_norm.items():
            if orig in used:
                continue
            if nk.startswith(pref + "-") or pref.startswith(nk + "-"):
                ranked.append(orig)
                used.add(orig)
                break
    for k in usable:
        if k not in used:
            rest.append(k)
    return ranked + rest


def _ordered_formats(formats: list[Any]) -> list[dict[str, Any]]:
    usable = [f for f in formats if isinstance(f, dict) and f.get("url")]
    by_ext = {str(f.get("ext") or "").lower(): f for f in usable}
    ordered: list[dict[str, Any]] = []
    used: set[int] = set()
    for ext in EXT_PREF:
        f = by_ext.get(ext)
        if f is not None and id(f) not in used:
            ordered.append(f)
            used.add(id(f))
    for f in usable:
        if id(f) not in used:
            ordered.append(f)
            used.add(id(f))
    return ordered


def parse_caption_payload(raw: bytes, ext: str) -> list[Cue]:
    if not raw or not raw.strip():
        return []
    text = raw.decode("utf-8-sig", errors="replace")
    ext = (ext or "").lower()
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("[") or ext in {"json3", "srv3", "json"}:
        try:
            return _parse_jsonish(text)
        except (json.JSONDecodeError, DownloadError, TypeError, ValueError):
            if "-->" in text:
                return _parse_vtt(text)
            return []
    if ext == "srt":
        return _parse_srt(text)
    return _parse_vtt(text)


def _parse_jsonish(text: str) -> list[Cue]:
    data = json.loads(text)
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        nested = data["data"]
        if isinstance(nested.get("body"), list) or isinstance(nested.get("events"), list):
            data = nested
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        cues: list[Cue] = []
        for ev in data["events"]:
            if not isinstance(ev, dict):
                continue
            segs = ev.get("segs") or []
            piece = "".join(str(s.get("utf8") or "") for s in segs if isinstance(s, dict))
            piece = piece.replace("\n", " ").strip()
            if not piece or piece == "\n":
                continue
            start = float(ev.get("tStartMs") or 0) / 1000.0
            dur = float(ev.get("dDurationMs") or 0) / 1000.0
            cues.append({"start": start, "end": start + dur, "text": piece})
        return cues
    body = data.get("body") if isinstance(data, dict) else None
    if isinstance(body, list):
        cues = []
        for item in body:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            start = float(item.get("from") or 0)
            end = float(item.get("to") or start)
            cues.append({"start": start, "end": end, "text": content})
        return cues
    raise DownloadError("无法解析该字幕 JSON")


_TS = re.compile(
    r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
)


def _ts_to_sec(h: str | None, m: str, s: str, ms: str) -> float:
    hours = int(h or 0)
    milli = int(ms.ljust(3, "0")[:3])
    return hours * 3600 + int(m) * 60 + int(s) + milli / 1000.0


def _parse_vtt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() and not ln.strip().startswith("WEBVTT")]
        if not lines:
            continue
        match = None
        idx = 0
        for i, ln in enumerate(lines):
            match = _TS.search(ln)
            if match:
                idx = i
                break
        if not match:
            continue
        start = _ts_to_sec(match.group(1), match.group(2), match.group(3), match.group(4))
        end = _ts_to_sec(match.group(5), match.group(6), match.group(7), match.group(8))
        body_lines = []
        for ln in lines[idx + 1 :]:
            cleaned = re.sub(r"<[^>]+>", "", ln).strip()
            if cleaned and not cleaned.startswith("NOTE"):
                body_lines.append(cleaned)
        body = " ".join(body_lines).strip()
        if body:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def _parse_srt(text: str) -> list[Cue]:
    return _parse_vtt(text)


def transcript_plain(cues: list[Cue], max_chars: int) -> str:
    parts: list[str] = []
    size = 0
    for cue in cues:
        line = f"[{format_timestamp(cue['start'])}] {cue['text']}"
        extra = len(line) + 1
        if size + extra > max_chars:
            parts.append("\n…（后续字幕已截断）")
            break
        parts.append(line)
        size += extra
    return "\n".join(parts)


def fetch_cues_for_url(url: str) -> tuple[list[Cue], str, str, str]:
    """Return cues, lang, source, title. Raises DownloadError."""
    if is_douyin_url(url):
        raise DownloadError(
            "抖音当前没有可用字幕轨，无法生成学习笔记。请换有字幕的 B 站或 YouTube 讲解。"
        )
    ydl_opts = build_ydl_opts(
        url,
        skip_download=True,
        writesubtitles=True,
        writeautomaticsub=True,
    )
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise DownloadError("无法解析该链接")
            if info.get("_type") == "playlist":
                entries = info.get("entries") or []
                info = next((e for e in entries if e), None)
                if not info:
                    raise DownloadError("播放列表为空，请粘贴单条视频链接")
            tracks = iter_caption_tracks(info)
            if not tracks:
                raise DownloadError(
                    "这个视频没有可用字幕（含自动字幕），第一期不做语音转写。请换有字幕的公开视频。"
                )
            referer = str(info.get("webpage_url") or url)
            last_err = "字幕文件为空或无法解析"
            for lang, source, track in tracks:
                try:
                    raw = _read_track_bytes(ydl, str(track["url"]), referer=referer)
                    cues = parse_caption_payload(raw, str(track.get("ext") or "vtt"))
                except Exception as exc:
                    last_err = f"拉取字幕失败：{exc}"
                    continue
                if cues:
                    title = str(info.get("title") or "未命名视频")
                    return cues, lang, source, title
            raise DownloadError(last_err)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"拉取字幕失败：{exc}") from exc


def _read_track_bytes(ydl: YoutubeDL, sub_url: str, referer: str = "") -> bytes:
    try:
        with ydl.urlopen(sub_url) as resp:
            data = resp.read()
            if data and data.strip():
                return data
    except Exception:
        data = b""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer
    if "bilibili.com" in (referer or "") or "hdslb.com" in sub_url:
        headers.setdefault("Referer", "https://www.bilibili.com/")
        headers["Origin"] = "https://www.bilibili.com"
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        resp = client.get(sub_url, headers=headers)
        resp.raise_for_status()
        return resp.content
