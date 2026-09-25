from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from config import DOWNLOADS_DIR


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class VideoDownloader:
    def get_info(self, url: str) -> dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
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
                return ydl.sanitize_info(info)
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(str(exc)) from exc

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

    def download(self, url: str, format_id: str, out_dir: Path, merge_audio: bool = False) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        fmt_spec = f"{format_id}+bestaudio/{format_id}" if merge_audio else format_id
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": fmt_spec,
            "outtmpl": str(out_dir / "%(title).80s.%(ext)s"),
            "merge_output_format": "mp4",
            "restrictfilenames": False,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() not in {".json", ".part"}]
        if not files:
            raise DownloadError("下载完成但未找到输出文件")
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]


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
