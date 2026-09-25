from __future__ import annotations

from typing import Any, Literal

from config import DIRECT_UNRELIABLE_EXTRACTORS, FRAGMENT_PROTOCOLS

Mode = Literal["server", "redirect", "proxy"]

# auto 模式下这些站几乎总是走 server。下载时跳过第二次 get_info。
# 抖音不在这里：下载仍走 get_info，但会命中解析缓存，不会再开浏览器。
_SERVER_HOST_MARKERS = (
    "youtube.com",
    "youtu.be",
    "bilibili.com",
    "b23.tv",
)


def skip_redownload_info_probe(url: str, prefer: str = "auto") -> bool:
    """解析页已拉过元数据时，下载阶段是否可直接落盘而不再 extract_info。"""
    if prefer == "server":
        return True
    if prefer == "direct":
        return False
    low = (url or "").lower()
    return any(marker in low for marker in _SERVER_HOST_MARKERS)


def _extractor_key(info: dict[str, Any]) -> str:
    return str(info.get("extractor_key") or info.get("extractor") or "").lower()


def needs_merge(fmt: dict[str, Any]) -> bool:
    vcodec = fmt.get("vcodec")
    acodec = fmt.get("acodec")
    has_v = vcodec not in (None, "none")
    has_a = acodec not in (None, "none")
    requested = fmt.get("requested_formats")
    if requested and len(requested) > 1:
        return True
    return has_v and not has_a


def is_fragment_protocol(fmt: dict[str, Any]) -> bool:
    proto = str(fmt.get("protocol") or "").lower()
    if proto in FRAGMENT_PROTOCOLS:
        return True
    if "m3u8" in proto or "dash" in proto:
        return True
    return False


def choose_mode(
    info: dict[str, Any],
    fmt: dict[str, Any],
    prefer: str = "auto",
) -> tuple[Mode, str]:
    url = (fmt.get("url") or "").strip()
    extractor = _extractor_key(info)

    if prefer == "server":
        return "server", "用户指定服务端下载"

    if is_fragment_protocol(fmt) or needs_merge(fmt):
        return "server", "分片流或音视频分离，需服务端合并"
    if not url:
        return "server", "该清晰度没有可用直链"

    if extractor in DIRECT_UNRELIABLE_EXTRACTORS:
        if prefer == "direct":
            return "proxy", "平台直链对浏览器不稳定，使用服务端代理"
        return "server", "该平台直链易失效，建议服务端下载"

    headers = fmt.get("http_headers") or {}
    needs_headers = bool(headers.get("Referer") or headers.get("Cookie") or headers.get("Authorization"))

    if prefer == "direct":
        return ("proxy" if needs_headers else "redirect"), "用户优先直链"

    if needs_headers:
        return "proxy", "直链需要特殊请求头，使用服务端代理"

    return "redirect", "单文件直链，可重定向下载"
