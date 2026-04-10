# 담당 : A팀원 유가영
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# 페르소나 생성
class PersonaCreate(BaseModel):
    name: str = Field(..., max_length=50, description="페르소나 이름 (예: 다정이)")
    preset_type: str | None = Field(
        None,
        description="empathy(공감형) | advice(조언형) | info(정보제공형) | custom(직접입력)"
    )
    custom_description: str | None = Field(
        None,
        description="preset_type=custom일 때 직접 입력하는 말투/성격 설명"
    )

# 페르소나 수정
class PersonaUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    preset_type: str | None = None
    custom_description: str | None = None
    is_active: bool | None = None

# 온보딩 Q&A 요청
class PersonaOnboardingRequest(BaseModel):
    name: str = Field(..., max_length=50, description="말벗 이름")
    nickname: str = Field(..., description="사용자 호칭")
    pace: str = Field(..., description="하루 페이스")
    reason: str = Field(..., description="일기 쓰는 이유")
    style: str = Field(..., description="원하는 말벗 스타일")
    memory: str | None = Field(None, description="기억해줬으면 하는 것 (선택)")
    voice: str | None = Field(None, description="TTS 목소리 (alloy | nova | echo | fable | onyx | shimmer)")
    image_url: str | None = Field(None, description="아바타 이미지 경로")

# 페르소나 응답
class PersonaResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    preset_type: str | None
    custom_description: str | None
    image_url: str | None
    voice: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
