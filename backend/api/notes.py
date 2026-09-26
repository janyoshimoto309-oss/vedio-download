from __future__ import annotations

from fastapi import APIRouter, HTTPException
from yt_dlp.utils import DownloadError

from config import OPENAI_MODEL, SUMMARIZE_MAX_CHARS
from models.notes_schemas import OutlineItem, SummarizeRequest, SummarizeResponse, TranscriptCue
from services.captions import fetch_cues_for_url, format_timestamp, transcript_plain
from services.llm import LLMError, llm_configured
from services.notes import build_markdown, summarize_part
from services.url_normalize import extract_video_url

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("/ready")
def notes_ready():
    ok = llm_configured()
    return {"llm": ok, "llm_model": OPENAI_MODEL if ok else None}


@router.post("/summarize", response_model=SummarizeResponse)
def video_summarize(body: SummarizeRequest) -> SummarizeResponse:
    if body.part != "transcript" and not llm_configured():
        raise HTTPException(
            status_code=503,
            detail="未配置 DeepSeek。请在 backend/.env 填写 DEEPSEEK_API_KEY 后重启后端。",
        )
    url = extract_video_url(body.url)
    try:
        cues, lang, source, title = fetch_cues_for_url(url)
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"拉取字幕失败：{exc}") from exc

    kwargs: dict = {}
    if body.part == "transcript":
        kwargs["cues"] = cues
    else:
        transcript = transcript_plain(cues, SUMMARIZE_MAX_CHARS)
        try:
            notes = summarize_part(body.part, title, transcript)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        kwargs.update(notes)

    markdown = build_markdown(title, url, lang, source, **kwargs)
    transcript_cues = []
    if body.part == "transcript":
        transcript_cues = [
            TranscriptCue(
                start=c["start"],
                end=c["end"],
                timestamp=format_timestamp(c["start"]),
                text=c["text"],
            )
            for c in cues
        ]
    return SummarizeResponse(
        part=body.part,
        title=title,
        webpage_url=url,
        language=lang,
        source=source,
        outline=kwargs.get("outline") or [],
        key_points=kwargs.get("key_points") or [],
        mind_map=kwargs.get("mind_map"),
        transcript=transcript_cues,
        markdown=markdown,
    )
