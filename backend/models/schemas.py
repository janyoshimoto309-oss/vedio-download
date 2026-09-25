from typing import Literal, Optional

from pydantic import BaseModel, Field

PreferMode = Literal["auto", "server", "direct"]
DownloadMode = Literal["server", "redirect", "proxy"]
StreamKind = Literal["muxed", "merge", "audio"]


class VideoInfoRequest(BaseModel):
    url: str = Field(..., min_length=8)


class FormatItem(BaseModel):
    format_id: str
    ext: str
    resolution: str
    filesize: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    protocol: Optional[str] = None
    stream_kind: StreamKind


class VideoInfoResponse(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    extractor: str
    webpage_url: str
    recommended_mode: DownloadMode
    recommended_reason: str
    formats: list[FormatItem]


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=8)
    format_id: str
    prefer_mode: PreferMode = "auto"


class DownloadResponse(BaseModel):
    mode: DownloadMode
    filename: str
    download_url: Optional[str] = None
    redirect_url: Optional[str] = None
    expires_at: Optional[str] = None
    fallback: bool = False
    reason: Optional[str] = None
