from typing import Literal, Optional

from pydantic import BaseModel, Field

NotePart = Literal["outline", "points", "map", "transcript"]


class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=8)
    part: NotePart


class TranscriptCue(BaseModel):
    start: float
    end: float
    timestamp: str
    text: str


class OutlineItem(BaseModel):
    start: float
    timestamp: str
    title: str
    summary: str = ""


class MindMapNode(BaseModel):
    label: str
    children: list["MindMapNode"] = []


class SummarizeResponse(BaseModel):
    part: NotePart
    title: str
    webpage_url: str
    language: str
    source: str
    outline: list[OutlineItem] = []
    key_points: list[str] = []
    mind_map: Optional[MindMapNode] = None
    transcript: list[TranscriptCue] = []
    markdown: str


MindMapNode.model_rebuild()
