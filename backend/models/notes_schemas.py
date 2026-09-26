from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    url: str = Field(..., min_length=8)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=16)

    @model_validator(mode="after")
    def last_must_be_user(self):
        if self.messages[-1].role != "user":
            raise ValueError("最后一条必须是用户提问")
        return self


class ChatResponse(BaseModel):
    reply: str
