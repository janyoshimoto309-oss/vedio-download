from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

import httpx

from config import COOKIES_FILE, COOKIES_FROM_BROWSER, DOWNLOADS_DIR, YTDLP_IMPERSONATE
from services.douyin_browser import extract_douyin_in_browser
from services.url_normalize import extract_video_url, is_douyin_url

_COOKIE_HINT = (
    "抖音需要新鲜访客 Cookie。请先在浏览器打开该视频（过完验证码即可，不必登录），"
    "把 Netscape 格式的 cookies.txt 放到 backend/cookies.txt，"
    "或设置环境变量 YTDLP_COOKIES_FROM_BROWSER=chrome 后重启后端再试。"
)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _is_douyin(url: str) -> bool:
    return is_douyin_url(url)


def _impersonate_target():
    if not YTDLP_IMPERSONATE:
        return None
    try:
        import curl_cffi  # noqa: F401
        from yt_dlp.networking.impersonate import ImpersonateTarget

        return ImpersonateTarget(YTDLP_IMPERSONATE)
    except Exception:
        return None


def build_ydl_opts(url: str | None = None, **extra: Any) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    # Cookie / 伪装只用于抖音 yt-dlp 回退，避免拖慢 YouTube / B 站等
    if url and _is_douyin(url):
        if COOKIES_FILE.is_file() and COOKIES_FILE.stat().st_size > 0:
            opts["cookiefile"] = str(COOKIES_FILE)
        if COOKIES_FROM_BROWSER:
            opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)
        opts["http_headers"] = {
            "Referer": "https://www.douyin.com/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        target = _impersonate_target()
        if target is not None:
            opts["impersonate"] = target
    opts.update(extra)
    return opts


def _rewrite_error(url: str, exc: BaseException) -> DownloadError:
    msg = str(exc)
    if _is_douyin(url) and (
        "Fresh cookies" in msg
        or "Failed to parse JSON" in msg
        or "s_v_web_id" in msg
    ):
        return DownloadError(_COOKIE_HINT)
    return exc if isinstance(exc, DownloadError) else DownloadError(msg)


class VideoDownloader:
    _info_cache: dict[str, dict[str, Any]] = {}

    def get_info(self, url: str) -> dict[str, Any]:
        url = extract_video_url(url)
        cached = self._info_cache.get(url)
        if cached is not None:
            return cached
        if _is_douyin(url):
            try:
                info = extract_douyin_in_browser(url)
                self._info_cache[url] = info
                return info
            except DownloadError:
                pass
        ydl_opts = build_ydl_opts(url, skip_download=True)
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise DownloadError("无法解析该链接")
                if info.get("_type") == "playlist":
                    entries = info.get("entries") or []
                    first = next((e for e in entries if e), None)
                    if not first:
                        raise DownloadError("播放列表为空，请粘贴单条视频链接")
                    info = first
                sanitized = ydl.sanitize_info(info)
                self._info_cache[url] = sanitized
                return sanitized
        except DownloadError as exc:
            raise _rewrite_error(url, exc) from exc
        except Exception as exc:
            raise _rewrite_error(url, exc) from exc

    def get_format(self, info: dict[str, Any], format_id: str) -> Optional[dict[str, Any]]:
        for item in info.get("formats") or []:
            if str(item.get("format_id")) == str(format_id):
                return item
        requested = info.get("requested_formats") or []
        for item in requested:
            if str(item.get("format_id")) == str(format_id):
                return item
        if str(info.get("format_id")) == str(format_id):
            return info
        return None

    def download(
        self,
        url: str,
        format_id: str,
        out_dir: Path,
        merge_audio: bool = False,
        cached_info: dict[str, Any] | None = None,
    ) -> Path:
        url = extract_video_url(url)
        out_dir.mkdir(parents=True, exist_ok=True)
        if _is_douyin(url):
            info = cached_info if cached_info is not None else self.get_info(url)
            fmt = self.get_format(info, format_id) or (info.get("formats") or [None])[0]
            if fmt and (fmt.get("url") or "").startswith("http"):
                return _download_direct(fmt, info.get("title") or "video", out_dir)
        fmt_spec = f"{format_id}+bestaudio/{format_id}" if merge_audio else format_id
        ydl_opts = build_ydl_opts(
            url,
            format=fmt_spec,
            outtmpl=str(out_dir / "%(title).80s.%(ext)s"),
            merge_output_format="mp4",
            restrictfilenames=False,
        )
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() not in {".json", ".part"}]
        if not files:
            raise DownloadError("下载完成但未找到输出文件")
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]


def _safe_file_stem(name: str) -> str:
    cleaned = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "video"
    return cleaned[:80]


def _download_direct(fmt: dict[str, Any], title: str, out_dir: Path) -> Path:
    media = (fmt.get("url") or "").strip()
    if not media:
        raise DownloadError("没有可下载的直链")
    headers = {str(k): str(v) for k, v in (fmt.get("http_headers") or {}).items()}
    dest = out_dir / f"{_safe_file_stem(title)}.mp4"
    with httpx.Client(timeout=httpx.Timeout(120.0, connect=20.0), follow_redirects=True) as client:
        with client.stream("GET", media, headers=headers) as resp:
            if resp.status_code >= 400:
                raise DownloadError(f"拉取视频失败：HTTP {resp.status_code}")
            with dest.open("wb") as fh:
                for chunk in resp.iter_bytes(64 * 1024):
                    fh.write(chunk)
    if dest.stat().st_size < 1024:
        dest.unlink(missing_ok=True)
        raise DownloadError("下载文件过小，直链可能已失效")
    return dest


def list_user_formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    raw = info.get("formats") or []
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for fmt in raw:
        if fmt.get("vcodec") == "none" and fmt.get("acodec") == "none":
            continue
        fid = str(fmt.get("format_id") or "")
        if not fid or fid in seen:
            continue
        proto = str(fmt.get("protocol") or "")
        if proto.startswith("mhtml") or proto == "storyboard":
            continue
        height = fmt.get("height")
        width = fmt.get("width")
        if height:
            resolution = f"{height}p"
        elif width:
            resolution = f"{width}w"
        elif fmt.get("vcodec") in (None, "none") and fmt.get("acodec") not in (None, "none"):
            resolution = "audio"
        else:
            resolution = str(fmt.get("format_note") or fmt.get("resolution") or "unknown")

        has_video = fmt.get("vcodec") not in (None, "none")
        has_audio = fmt.get("acodec") not in (None, "none")
        if has_video and has_audio:
            stream_kind = "muxed"
        elif has_video:
            stream_kind = "merge"
        elif has_audio:
            stream_kind = "audio"
        else:
            continue

        seen.add(fid)
        result.append(
            {
                "format_id": fid,
                "ext": fmt.get("ext") or "mp4",
                "resolution": resolution,
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "vcodec": None if fmt.get("vcodec") in (None, "none") else fmt.get("vcodec"),
                "acodec": None if fmt.get("acodec") in (None, "none") else fmt.get("acodec"),
                "protocol": fmt.get("protocol"),
                "stream_kind": stream_kind,
                "_sort_height": height or 0,
                "_has_video": has_video,
                "_has_audio": has_audio,
            }
        )

    result.sort(key=lambda x: (x["_has_video"], x["_sort_height"], x["_has_audio"]), reverse=True)
    for item in result:
        item.pop("_sort_height", None)
        item.pop("_has_video", None)
        item.pop("_has_audio", None)
    return result[:40]


DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
