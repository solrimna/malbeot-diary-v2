from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()
user_svc = UserService()


# ── GET /users/me ─ 내 프로필 조회 ───────────────
@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return await user_svc.get_me(current_user)


# ── PATCH /users/me ─ 내 프로필 수정 ─────────────
@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_svc.update_me(db, current_user, body)


# ── DELETE /users/me ─ 회원 탈퇴 ─────────────────
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_svc.delete_me(db, current_user)
