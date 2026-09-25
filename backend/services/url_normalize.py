from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_PREFERRED_HOSTS = (
    "v.douyin.com",
    "www.douyin.com",
    "douyin.com",
    "www.iesdouyin.com",
    "iesdouyin.com",
)


def extract_video_url(raw: str) -> str:
    """从分享文案或纯链接中抽出第一条可用 URL（优先抖音），并归一化弹窗页。"""
    text = (raw or "").strip()
    if not text:
        return text

    candidates = [_trim_url(m.group(0)) for m in _URL_RE.finditer(text)]
    if not candidates:
        picked = text.split()[0] if text.split() else text
    else:
        picked = candidates[0]
        for url in candidates:
            host = _host(url)
            if any(host == h or host.endswith("." + h) for h in _PREFERRED_HOSTS):
                picked = url
                break
    return canonicalize_douyin(picked)


def is_douyin_url(url: str) -> bool:
    host = _host(url)
    return host == "douyin.com" or host.endswith(".douyin.com") or host == "iesdouyin.com" or host.endswith(".iesdouyin.com")


def canonicalize_douyin(url: str) -> str:
    """把用户主页/搜索弹窗链接改写成 /video/{id}，供 yt-dlp Douyin extractor 识别。"""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if "douyin.com" not in host:
        return url

    path = parsed.path or ""
    m = re.search(r"/(?:video|note|share/video)/(\d+)", path)
    if m:
        return f"https://www.douyin.com/video/{m.group(1)}"

    qs = parse_qs(parsed.query)
    for key in ("modal_id", "vid"):
        value = (qs.get(key) or [None])[0]
        if value and str(value).isdigit():
            return f"https://www.douyin.com/video/{value}"
    return url


def _trim_url(url: str) -> str:
    return url.rstrip(").,;!?]}》」』、。")


def _host(url: str) -> str:
    try:
        after = url.split("://", 1)[1]
        return after.split("/", 1)[0].split("?", 1)[0].lower()
    except IndexError:
        return ""
