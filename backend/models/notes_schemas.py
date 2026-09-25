from typing import Optional

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=8)


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
    title: str
    webpage_url: str
    language: str
    source: str
    overview: str
    outline: list[OutlineItem]
    key_points: list[str]
    mind_map: MindMapNode
    transcript: list[TranscriptCue]
    markdown: str


MindMapNode.model_rebuild()
