import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── 회원가입 요청 데이터 ──────────────────────────
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    nickname: str = Field(min_length=1, max_length=50)


# ── 로그인 요청 데이터 ───────────────────────────
class UserLogin(BaseModel):
    username: str
    password: str


# ── 유저 응답 데이터 (비밀번호 제외) ──────────────
class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    nickname: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── 프로필 응답 데이터 (profile_image_url 포함) ───
class UserProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    nickname: str
    profile_image_url: str | None
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True


# ── 프로필 수정 요청 데이터 (모두 선택) ──────────
class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    profile_image_url: str | None = Field(default=None, max_length=500)


# ── 토큰 응답 데이터 ─────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
