from __future__ import annotations

import json
import re
from typing import Any

import httpx
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from services.downloader import VideoDownloader, build_ydl_opts
from services.douyin_browser import _captions_from_render, _id_from_url, extract_douyin_in_browser
from services.url_normalize import extract_video_url, is_douyin_url

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
_CUE_CACHE: dict[str, tuple[list[Cue], str, str, str]] = {}


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
                inline = str(fmt.get("data") or "")
                if not url and not inline.strip():
                    continue
                key = url or f"inline:{lang}:{source}:{id(fmt)}"
                if key in seen:
                    continue
                seen.add(key)
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
    usable = [
        f
        for f in formats
        if isinstance(f, dict) and (f.get("url") or str(f.get("data") or "").strip())
    ]
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
        cues = _cues_from_list(body)
        if cues:
            return cues
    if isinstance(data, list):
        cues = _cues_from_list(data)
        if cues:
            return cues
    utterances = data.get("utterances") if isinstance(data, dict) else None
    if isinstance(utterances, list):
        cues = _cues_from_list(utterances)
        if cues:
            return cues
    raise DownloadError("无法解析该字幕 JSON")


_MS_TIME_KEYS = {
    "starttime",
    "start_time",
    "tstartms",
    "endtime",
    "end_time",
    "tendms",
    "ddurationms",
}


def _cues_from_list(items: list[Any]) -> list[Cue]:
    cues: list[Cue] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = str(
            item.get("content") or item.get("text") or item.get("utf8") or ""
        ).strip()
        if not content:
            continue
        start, start_key = _first_time(
            item, ("from", "start", "startTime", "start_time", "tStartMs")
        )
        start = _ms_or_sec(start, start_key) if start is not None else 0.0
        end, end_key = _first_time(
            item, ("to", "end", "endTime", "end_time", "tEndMs")
        )
        if end is None and item.get("dDurationMs") is not None:
            end = start + float(item.get("dDurationMs") or 0) / 1000.0
        elif end is None:
            end = start
        else:
            end = _ms_or_sec(end, end_key)
        cues.append({"start": start, "end": end, "text": content})
    return cues


def _first_time(item: dict[str, Any], keys: tuple[str, ...]) -> tuple[float | None, str]:
    for key in keys:
        if item.get(key) is not None:
            return float(item.get(key) or 0), key
    return None, ""


def _ms_or_sec(value: float | None, key: str) -> float:
    num = float(value or 0)
    if key.replace("-", "_").lower() in _MS_TIME_KEYS:
        return num / 1000.0
    return num


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


def clear_cue_cache() -> None:
    _CUE_CACHE.clear()


def fetch_cues_for_url(url: str) -> tuple[list[Cue], str, str, str]:
    """Return cues, lang, source, title. Raises DownloadError."""
    key = extract_video_url(url)
    cached = _CUE_CACHE.get(key)
    if cached is not None:
        return cached
    result = _fetch_cues_uncached(key)
    _CUE_CACHE[key] = result
    return result


def _fetch_cues_uncached(url: str) -> tuple[list[Cue], str, str, str]:
    if is_douyin_url(url):
        return _fetch_douyin_cues(url)
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
            return _cues_from_info(ydl, info, url)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"拉取字幕失败：{exc}") from exc


def _fetch_douyin_cues(url: str) -> tuple[list[Cue], str, str, str]:
    downloader = VideoDownloader()
    info = downloader.get_info(url)
    if not iter_caption_tracks(info):
        _merge_caption_buckets(info, *_aweme_caption_buckets(url))
        if not iter_caption_tracks(info) and str(info.get("extractor") or "") != "DouyinBrowser":
            try:
                fresh = extract_douyin_in_browser(url)
                _merge_caption_buckets(
                    info, fresh.get("subtitles") or {}, fresh.get("automatic_captions") or {}
                )
                if fresh.get("title"):
                    info["title"] = fresh["title"]
                if fresh.get("webpage_url"):
                    info["webpage_url"] = fresh["webpage_url"]
            except DownloadError:
                pass
        downloader._info_cache[url] = info
    ydl_opts = build_ydl_opts(url, skip_download=True)
    with YoutubeDL(ydl_opts) as ydl:
        try:
            return _cues_from_info(ydl, info, url)
        except DownloadError as exc:
            msg = str(exc)
            if "没有可用字幕" in msg or "只有弹幕" in msg:
                raise DownloadError(
                    "这个抖音视频没有可下载的字幕轨（画面上烧进去的字不算）。"
                    "第一期不做语音转写。请换油管带 CC / 自动字幕的讲解。"
                ) from exc
            raise


def _merge_caption_buckets(
    info: dict[str, Any],
    official: dict[str, list[dict[str, Any]]],
    auto: dict[str, list[dict[str, Any]]],
) -> None:
    if official:
        bucket = info.setdefault("subtitles", {})
        for lang, tracks in official.items():
            bucket.setdefault(lang, []).extend(tracks)
    if auto:
        bucket = info.setdefault("automatic_captions", {})
        for lang, tracks in auto.items():
            bucket.setdefault(lang, []).extend(tracks)


def _aweme_caption_buckets(
    url: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    official: dict[str, list[dict[str, Any]]] = {}
    auto: dict[str, list[dict[str, Any]]] = {}
    aweme_id = _id_from_url(url)
    try:
        ydl_opts = build_ydl_opts(url, skip_download=True)
        with YoutubeDL(ydl_opts) as ydl:
            ie = ydl.get_info_extractor("Douyin")
            raw = ie._download_json(
                "https://www.douyin.com/aweme/v1/web/aweme/detail/",
                aweme_id,
                query={"aweme_id": aweme_id},
                fatal=False,
            )
        detail = (raw or {}).get("aweme_detail") if isinstance(raw, dict) else None
        dumped = json.dumps(detail or {}, ensure_ascii=False)
        tracks = _captions_from_render(dumped, aweme_id if aweme_id != "douyin" else None)
        for track in tracks:
            lang = str(track.get("lang") or "zh")
            bucket = auto if track.get("source") == "auto" else official
            bucket.setdefault(lang, []).append(track["fmt"])
    except Exception:
        return official, auto
    return official, auto


MAX_TRACK_TRIES = 8


def _empty_caption_error(info: dict[str, Any]) -> str:
    keys = list((info.get("subtitles") or {}).keys()) + list((info.get("automatic_captions") or {}).keys())
    usable = [k for k in keys if _norm_lang(k) not in SKIP_LANGS]
    if keys and not usable:
        return (
            "这个视频只有弹幕、没有字幕轨。第一期不做语音转写。"
            "请换油管带 CC / 自动字幕的讲解。"
        )
    return (
        "这个视频没有可用字幕（含自动字幕），第一期不做语音转写。"
        "请换油管带 CC / 自动字幕的讲解。"
    )


def _is_rate_limited(exc: BaseException) -> bool:
    msg = str(exc)
    return "429" in msg or "Too Many Requests" in msg


def _cues_from_info(ydl: YoutubeDL, info: dict[str, Any], url: str) -> tuple[list[Cue], str, str, str]:
    tracks = iter_caption_tracks(info)
    if not tracks:
        raise DownloadError(_empty_caption_error(info))
    referer = str(info.get("webpage_url") or url)
    last_err = "字幕文件为空或无法解析"
    for lang, source, track in tracks[:MAX_TRACK_TRIES]:
        try:
            inline = track.get("data")
            if isinstance(inline, str) and inline.strip():
                raw = inline.encode("utf-8")
            else:
                raw = _read_track_bytes(ydl, str(track.get("url") or ""), referer=referer)
            cues = parse_caption_payload(raw, str(track.get("ext") or "vtt"))
        except Exception as exc:
            if _is_rate_limited(exc):
                raise DownloadError("字幕接口暂时限流，请过一两分钟再点生成学习笔记。") from exc
            last_err = f"拉取字幕失败：{exc}"
            continue
        if cues:
            title = str(info.get("title") or "未命名视频")
            return cues, lang, source, title
    raise DownloadError(last_err)


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
    if "douyin.com" in (referer or "") or "douyin" in sub_url:
        headers["Referer"] = "https://www.douyin.com/"
        headers["Origin"] = "https://www.douyin.com"
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True) as client:
        resp = client.get(sub_url, headers=headers)
        resp.raise_for_status()
        return resp.content
