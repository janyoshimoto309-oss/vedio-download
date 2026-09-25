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

    def on_response(response) -> None:
        url = response.url or ""
        if _looks_like_media(url):
            captured.append(url)

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
  return {
    title: document.title || '',
    thumbnail: (og && og.content) || main.poster || '',
    duration: (main.duration && isFinite(main.duration)) ? main.duration : null,
    mainSrc: main.src || '',
    videoSrcs: playable.map(v => v.src),
    renderText: render ? render.textContent : ''
  };
}"""


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
