# 담당 : A팀원 유가영
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── 일기 생성할 때 받는 데이터 ──────────────────
class DiaryCreate(BaseModel):
    title: str | None = Field(None, max_length=200)
    emotion: str | None = Field(None, max_length=100)
    weather: str | None = Field(None, max_length=100)
    content: str
    diary_date: date
    input_type: str = "text"          # "text" | "voice" | "mixed"
    hashtags: list[str] = []          # 예: ["여행", "행복"]
    persona_id: uuid.UUID | None = None


# ── 일기 수정할 때 받는 데이터 ──────────────────
class DiaryUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    emotion: str | None = Field(None, max_length=100)
    weather: str | None = Field(None, max_length=100)
    content: str | None = None
    diary_date: date | None = None
    persona_id: uuid.UUID | None = None


# ── API가 응답할 때 보내는 데이터 ────────────────
class DiaryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    persona_id: uuid.UUID | None
    title: str | None
    emotion: str | None
    weather: str | None
    content: str
    input_type: str
    diary_date: date
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
