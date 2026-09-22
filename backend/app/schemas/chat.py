from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceItem(BaseModel):
    filename: str


class ChatResponse(BaseModel):
    answer: str
    tool_used: str | None
    sources: list[SourceItem]


class ChatHistoryItem(BaseModel):
    role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
