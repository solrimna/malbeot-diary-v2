from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:

    # ── 내 프로필 조회 ────────────────────────────
    async def get_me(self, user: User) -> User:
        return user

    # ── 내 프로필 수정 ────────────────────────────
    async def update_me(
        self,
        db: AsyncSession,
        user: User,
        data: UserUpdate,
    ) -> User:
        if data.nickname is not None:
            user.nickname = data.nickname

        if data.password is not None:
            try:
                user.password_hash = hash_password(data.password)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="비밀번호 해시 처리에 실패했습니다.",
                ) from None

        if data.profile_image_url is not None:
            user.profile_image_url = data.profile_image_url

        await db.commit()
        await db.refresh(user)
        return user

    # ── 회원 탈퇴 ────────────────────────────────
    async def delete_me(
        self,
        db: AsyncSession,
        user: User,
    ) -> None:
        await db.delete(user)
        await db.commit()
