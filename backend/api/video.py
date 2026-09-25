from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from yt_dlp.utils import DownloadError

from config import DOWNLOADS_DIR
from models.schemas import (
    DownloadRequest,
    DownloadResponse,
    FormatItem,
    VideoInfoRequest,
    VideoInfoResponse,
)
from services import proxy_token, task_store
from services.download_strategy import choose_mode, needs_merge
from services.downloader import VideoDownloader, ffmpeg_available, list_user_formats
from services.url_normalize import extract_video_url

router = APIRouter(prefix="/api/video", tags=["video"])
downloader = VideoDownloader()
TZ = timezone(timedelta(hours=8))


def _safe_filename(name: str) -> str:
    cleaned = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "video"
    return cleaned[:120]


def _pick_recommend_format(formats: list[dict], info: dict) -> dict | None:
    if not formats:
        return None
    fid = info.get("format_id")
    for f in formats:
        if fid and f["format_id"] == str(fid):
            return f
    for f in formats:
        if f.get("vcodec") and f.get("acodec"):
            return f
    return formats[0]


@router.post("/info", response_model=VideoInfoResponse)
def video_info(body: VideoInfoRequest) -> VideoInfoResponse:
    try:
        info = downloader.get_info(extract_video_url(body.url))
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析失败：{exc}") from exc

    formats = list_user_formats(info)
    rec_fmt = _pick_recommend_format(formats, info) or {}
    ytdlp_fmt = downloader.get_format(info, rec_fmt.get("format_id", "")) if rec_fmt else None
    mode, reason = choose_mode(info, ytdlp_fmt or rec_fmt, prefer="auto")

    return VideoInfoResponse(
        title=info.get("title") or "未命名视频",
        thumbnail=info.get("thumbnail"),
        duration=info.get("duration"),
        extractor=str(info.get("extractor") or info.get("extractor_key") or "unknown"),
        webpage_url=str(info.get("webpage_url") or body.url),
        recommended_mode=mode,
        recommended_reason=reason,
        formats=[FormatItem(**{k: v for k, v in f.items() if k in FormatItem.model_fields}) for f in formats],
    )


def _server_download(
    url: str,
    format_id: str,
    fallback: bool,
    reason: str,
    merge_audio: bool = False,
) -> DownloadResponse:
    if not task_store.acquire_slot():
        raise HTTPException(status_code=429, detail="当前下载任务过多，请稍后再试")
    task_dir = DOWNLOADS_DIR / uuid.uuid4().hex
    try:
        path = downloader.download(url, format_id, task_dir, merge_audio=merge_audio)
    except DownloadError as exc:
        shutil.rmtree(task_dir, ignore_errors=True)
        msg = str(exc)
        if "ffmpeg" in msg.lower() and not ffmpeg_available():
            raise HTTPException(
                status_code=500,
                detail="需要 ffmpeg 才能合并该清晰度。请安装 ffmpeg 并加入 PATH 后重试。",
            ) from exc
        raise HTTPException(status_code=400, detail=f"下载失败：{msg}") from exc
    except Exception as exc:
        shutil.rmtree(task_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"下载失败：{exc}") from exc
    finally:
        task_store.release_slot()

    filename = _safe_filename(path.name)
    rec = task_store.register_file(path, filename)
    expires = datetime.fromtimestamp(rec.expires_at, TZ).isoformat()
    return DownloadResponse(
        mode="server",
        filename=filename,
        download_url=f"/api/video/file/{rec.task_id}",
        expires_at=expires,
        fallback=fallback,
        reason=reason,
    )


@router.post("/download", response_model=DownloadResponse)
def video_download(body: DownloadRequest) -> DownloadResponse:
    url = extract_video_url(body.url)
    try:
        info = downloader.get_info(url)
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fmt = downloader.get_format(info, body.format_id)
    if fmt is None:
        raise HTTPException(status_code=400, detail="找不到所选清晰度，请重新解析")

    mode, reason = choose_mode(info, fmt, prefer=body.prefer_mode)
    title = _safe_filename((info.get("title") or "video") + "." + (fmt.get("ext") or "mp4"))
    media_url = (fmt.get("url") or "").strip()
    headers = {str(k): str(v) for k, v in (fmt.get("http_headers") or {}).items()}

    merge_audio = needs_merge(fmt)

    if mode == "server":
        return _server_download(
            url, body.format_id, fallback=False, reason=reason, merge_audio=merge_audio
        )

    if mode == "redirect" and media_url:
        return DownloadResponse(mode="redirect", filename=title, redirect_url=media_url, reason=reason)

    if mode == "proxy" and media_url:
        try:
            token = proxy_token.issue(media_url, headers, title)
            return DownloadResponse(
                mode="proxy",
                filename=title,
                download_url=f"/api/video/proxy/{token}",
                reason=reason,
            )
        except Exception:
            return _server_download(
                url,
                body.format_id,
                fallback=True,
                reason="直链签发失败，已回退服务端下载",
                merge_audio=merge_audio,
            )

    return _server_download(
        url,
        body.format_id,
        fallback=True,
        reason="直链不可用，已回退服务端下载",
        merge_audio=merge_audio,
    )


@router.get("/file/{task_id}")
def get_file(task_id: str):
    rec = task_store.get_task(task_id)
    if rec is None or not rec.path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期，请重新下载")
    encoded = quote(rec.filename)
    return FileResponse(
        path=rec.path,
        filename=rec.filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/proxy/{token}")
async def proxy_file(token: str):
    try:
        payload = proxy_token.verify(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    url = payload["u"]
    headers = payload.get("h") or {}
    filename = _safe_filename(payload.get("n") or "video")
    encoded = quote(filename)

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=True)
    try:
        req = client.build_request("GET", url, headers=headers)
        upstream = await client.send(req, stream=True)
    except Exception as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"代理拉取失败：{exc}") from exc

    if upstream.status_code >= 400:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"上游返回 {upstream.status_code}，请改用服务端下载")

    async def stream():
        try:
            async for chunk in upstream.aiter_bytes(1024 * 64):
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    media = upstream.headers.get("content-type") or "application/octet-stream"
    return StreamingResponse(
        stream(),
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
