from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote, urlparse

from yt_dlp.utils import DownloadError

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_REFERER = "https://www.douyin.com/"
_CDN_HINTS = ("douyinvod.com", "bytevod.com", "video/tos/")
_CDN_BLOCK = ("douyinstatic.com", "uuu_", "xgplayer", ".js")


def extract_douyin_in_browser(page_url: str, timeout_ms: int = 35000) -> dict[str, Any]:
    """用独立 Chromium 打开抖音页，从播放器/网络请求拿直链。不使用 cookies.txt。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise DownloadError("未安装 Playwright。请在 backend 虚拟环境执行: pip install playwright && playwright install chromium") from exc

    aweme_id = _id_from_url(page_url)
    captured: list[str] = []
    captured_captions: list[str] = []

    def on_response(response) -> None:
        url = response.url or ""
        if _looks_like_media(url):
            captured.append(url)
        if _looks_like_caption(url):
            captured_captions.append(url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = browser.new_context(
                locale="zh-CN",
                user_agent=_UA,
                viewport={"width": 1280, "height": 800},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
            )
            page = context.new_page()
            page.on("response", on_response)
            page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_function(
                    """() => {
                      const vs = [...document.querySelectorAll('video')];
                      return vs.some(v => {
                        const s = v.currentSrc || v.src || '';
                        return s.includes('douyinvod.com') || s.includes('video/tos/');
                      });
                    }""",
                    timeout=timeout_ms,
                )
            except Exception:
                try:
                    page.wait_for_event(
                        "response",
                        lambda r: _looks_like_media(r.url),
                        timeout=12000,
                    )
                except Exception:
                    page.wait_for_timeout(5000)
            snapshot = page.evaluate(_PAGE_JS)
            final_url = page.url
            browser.close()
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"无头浏览器打开抖音失败：{exc}") from exc

    target_id = _id_from_url(final_url) if _id_from_url(final_url) != "douyin" else aweme_id
    media = _pick_media(captured, snapshot, target_id)
    if not media:
        raise DownloadError("浏览器打开了页面，但没有拿到视频地址（可能出现验证码或该内容无法公开播放）")

    title = (snapshot.get("title") or "").replace(" - 抖音", "").strip() or "抖音视频"
    duration = snapshot.get("duration")
    if isinstance(duration, (int, float)) and duration and duration not in (float("inf"),):
        duration_val: float | None = float(duration)
    else:
        duration_val = None

    formats = []
    for i, src in enumerate(media):
        formats.append(
            {
                "format_id": f"browser-{i}",
                "url": src,
                "ext": "mp4",
                "protocol": "https",
                "vcodec": "h264",
                "acodec": "aac",
                "http_headers": {"Referer": _REFERER, "User-Agent": _UA},
                "height": _guess_height(src),
            }
        )

    thumb = snapshot.get("thumbnail") or None
    official, auto = _captions_from_snapshot(snapshot, target_id if target_id != "douyin" else None)
    _merge_caption_urls(official, captured_captions)
    return {
        "id": target_id,
        "title": title,
        "thumbnail": thumb,
        "duration": duration_val,
        "extractor": "DouyinBrowser",
        "extractor_key": "DouyinBrowser",
        "webpage_url": final_url or page_url,
        "formats": formats,
        "format_id": formats[0]["format_id"],
        "subtitles": official,
        "automatic_captions": auto,
    }


_PAGE_JS = """() => {
  const videos = [...document.querySelectorAll('video')].map(v => {
    const r = v.getBoundingClientRect();
    return {
      src: v.currentSrc || v.src || '',
      duration: v.duration,
      poster: v.poster || '',
      area: Math.max(0, r.width) * Math.max(0, r.height)
    };
  });
  const playable = videos.filter(v =>
    (v.src.includes('douyinvod.com') || v.src.includes('video/tos/')) && v.area > 0
  );
  playable.sort((a, b) => b.area - a.area);
  const main = playable[0] || videos.find(v => v.src.startsWith('http')) || {};
  const og = document.querySelector('meta[property="og:image"]');
  const render = document.getElementById('RENDER_DATA');
  const tracks = [...document.querySelectorAll('track')].map(t => ({
    src: t.src || t.getAttribute('src') || '',
    kind: t.kind || '',
    srclang: t.srclang || '',
    label: t.label || ''
  }));
  return {
    title: document.title || '',
    thumbnail: (og && og.content) || main.poster || '',
    duration: (main.duration && isFinite(main.duration)) ? main.duration : null,
    mainSrc: main.src || '',
    videoSrcs: playable.map(v => v.src),
    renderText: render ? render.textContent : '',
    htmlTracks: tracks
  };
}"""


def _looks_like_caption(url: str) -> bool:
    low = url.lower()
    if any(b in low for b in (".js", ".css", "captcha")):
        return False
    return any(h in low for h in ("caption", "subtitle", ".vtt", "webvtt", "/cla/"))


def _merge_caption_urls(official: dict[str, list[dict[str, Any]]], urls: list[str]) -> None:
    seen = {str(item.get("url") or "") for items in official.values() for item in items}
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        ext = "srt" if ".srt" in url.lower() else "vtt"
        official.setdefault("zh", []).append(
            {"url": url, "ext": ext, "http_headers": {"Referer": _REFERER, "User-Agent": _UA}}
        )


def _looks_like_media(url: str) -> bool:
    low = url.lower()
    if low.startswith("blob:"):
        return False
    if any(b in low for b in _CDN_BLOCK):
        return False
    return any(h in low for h in _CDN_HINTS)


def _pick_media(captured: list[str], snapshot: dict[str, Any], aweme_id: str) -> list[str]:
    matched = _urls_from_render(snapshot.get("renderText") or "", aweme_id if aweme_id != "douyin" else None)
    main = snapshot.get("mainSrc") or ""
    ordered: list[str] = []
    if isinstance(main, str) and main.startswith("http") and _looks_like_media(main):
        ordered.append(main)
    ordered.extend(matched)
    if not ordered:
        ordered.extend(reversed(captured))
    return _unique(ordered)


def _node_id(node: dict[str, Any]) -> str:
    for key in ("awemeId", "aweme_id", "groupId", "group_id", "aweme_id_str"):
        val = node.get(key)
        if val is not None and str(val).isdigit():
            return str(val)
    return ""


def _urls_from_render(text: str, aweme_id: str | None = None) -> list[str]:
    if not text:
        return []
    try:
        data = json.loads(unquote(text))
    except Exception:
        return re.findall(r"https://[^\"\\]+douyinvod[^\"\\]+", text)

    found: list[str] = []

    def collect_urls(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in {"src", "url", "playApi", "play_addr"} and isinstance(v, str) and v.startswith("http") and _looks_like_media(v):
                    found.append(v)
                elif k in {"url_list", "urlList"} and isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.startswith("http") and _looks_like_media(item):
                            found.append(item)
                else:
                    collect_urls(v)
        elif isinstance(node, list):
            for item in node:
                collect_urls(item)

    def walk_match(node: Any) -> None:
        if isinstance(node, dict):
            nid = _node_id(node)
            if aweme_id and nid == aweme_id:
                collect_urls(node)
                return
            for v in node.values():
                walk_match(v)
        elif isinstance(node, list):
            for item in node:
                walk_match(item)

    if aweme_id:
        walk_match(data)
        if found:
            return found
    collect_urls(data)
    return found


def _unique(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        key = url.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        result.append(url)
        if len(result) >= 8:
            break
    return result


def _guess_height(url: str) -> int | None:
    m = re.search(r"(?:_|/|ds=)(\d{3,4})p", url, re.I)
    if m:
        return int(m.group(1))
    return None


def _id_from_url(url: str) -> str:
    path = urlparse(url).path
    m = re.search(r"/video/(\d+)", path)
    return m.group(1) if m else "douyin"


_CAPTION_LIST_KEYS = {
    "captioninfos",
    "caption_infos",
    "subtitleinfos",
    "subtitle_infos",
    "auto_captions",
    "autocaptions",
}
_CAPTION_OBJECT_KEYS = {"clainfo", "cla_info"}


def _captions_from_snapshot(
    snapshot: dict[str, Any], aweme_id: str | None
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    official: dict[str, list[dict[str, Any]]] = {}
    auto: dict[str, list[dict[str, Any]]] = {}
    tracks = _captions_from_render(snapshot.get("renderText") or "", aweme_id)
    for item in snapshot.get("htmlTracks") or []:
        if not isinstance(item, dict):
            continue
        src = str(item.get("src") or "")
        if src.startswith("http"):
            tracks.append(
                {
                    "lang": str(item.get("srclang") or "zh") or "zh",
                    "source": "official",
                    "fmt": {"url": src, "ext": "vtt" if ".srt" not in src.lower() else "srt"},
                }
            )
    for track in tracks:
        lang = str(track.get("lang") or "zh")
        bucket = auto if track.get("source") == "auto" else official
        bucket.setdefault(lang, []).append(track["fmt"])
    return official, auto


def _captions_from_render(text: str, aweme_id: str | None = None) -> list[dict[str, Any]]:
    if not text:
        return []
    try:
        data = json.loads(unquote(text))
    except Exception:
        return []

    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_item(item: Any) -> None:
        track = _track_from_caption_item(item)
        if not track:
            return
        key = str(track["fmt"].get("url") or track["fmt"].get("data") or "")
        if not key or key in seen:
            return
        seen.add(key)
        found.append(track)

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                nk = str(k).replace("-", "_").lower()
                if nk in _CAPTION_LIST_KEYS and isinstance(v, list):
                    for item in v:
                        add_item(item)
                elif nk in _CAPTION_OBJECT_KEYS and isinstance(v, dict):
                    collect(v)
                else:
                    collect(v)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    def walk_match(node: Any) -> None:
        if isinstance(node, dict):
            nid = _node_id(node)
            if aweme_id and nid == aweme_id:
                collect(node)
                return
            for v in node.values():
                walk_match(v)
        elif isinstance(node, list):
            for item in node:
                walk_match(item)

    if aweme_id:
        walk_match(data)
    if not found:
        collect(data)
    return found


def _track_from_caption_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    url = ""
    for key in ("url", "Url", "uri", "src"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith("http"):
            url = val
            break
        if isinstance(val, dict) and not url:
            for entry in val.get("url_list") or val.get("urlList") or []:
                if isinstance(entry, str) and entry.startswith("http"):
                    url = entry
                    break
    if not url:
        for key in ("url_list", "urlList"):
            val = item.get(key)
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, str) and entry.startswith("http"):
                        url = entry
                        break
                    if isinstance(entry, dict):
                        nested = entry.get("url") or entry.get("src")
                        if isinstance(nested, str) and nested.startswith("http"):
                            url = nested
                            break
            if url:
                break
    inline = item.get("captionContent") or item.get("caption_content") or item.get("content")
    inline_text = inline.strip() if isinstance(inline, str) else ""
    if not url and not inline_text:
        return None
    lang = str(
        item.get("languageCode")
        or item.get("language_code")
        or item.get("lang")
        or item.get("language")
        or "zh"
    ).strip() or "zh"
    fmt_name = str(
        item.get("captionFormat") or item.get("caption_format") or item.get("format") or item.get("ext") or "webvtt"
    ).lower()
    if "srt" in fmt_name:
        ext = "srt"
    elif "json" in fmt_name:
        ext = "json"
    else:
        ext = "vtt"
    auto = bool(item.get("isAutoGenerated") or item.get("is_auto_generated") or item.get("auto"))
    fmt: dict[str, Any] = {"ext": ext}
    if url:
        fmt["url"] = url
        fmt["http_headers"] = {"Referer": _REFERER, "User-Agent": _UA}
    if inline_text:
        fmt["data"] = inline_text
    return {"lang": lang, "source": "auto" if auto else "official", "fmt": fmt}
