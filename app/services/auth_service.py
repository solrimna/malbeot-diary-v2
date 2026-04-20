import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.email_service import send_password_reset_email, send_verification_email


class AuthService:

    # ── 회원가입 ─────────────────────────────────
    async def register(self, db: AsyncSession, data: UserCreate) -> User:
        # 아이디 중복 확인 (대소문자 구분 없이)
        dup_username = await db.execute(
            select(User).where(func.lower(User.username) == data.username)
        )
        if dup_username.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다.")

        # 이메일 중복 확인
        dup_email = await db.execute(select(User).where(User.email == data.email))
        if dup_email.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")

        try:
            pw_hash = hash_password(data.password)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="비밀번호 해시 처리에 실패했습니다.",
            ) from None

        user = User(
            username=data.username,
            email=data.email,
            password_hash=pw_hash,
            nickname=data.nickname,
            auth_provider="local",
            is_verified=False,
        )
        db.add(user)
        await db.flush()  # user.id 확보 (commit 전)

        # 이메일 인증 토큰 생성 & 저장
        token_str = secrets.token_urlsafe(48)
        email_token = EmailToken(
            user_id=user.id,
            token=token_str,
            token_type="email_verification",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24),
        )
        db.add(email_token)
        await db.commit()
        await db.refresh(user)

        # 인증 메일 발송 (실패해도 가입은 완료 — 재발송 기능으로 처리)
        try:
            await send_verification_email(
                to_email=user.email,
                to_name=user.nickname,
                token=token_str,
            )
        except Exception:
            pass  # 메일 발송 실패 시 로그는 email_service 내부에서 기록

        return user

    # ── 이메일 인증 완료 ──────────────────────────
    async def verify_email(self, db: AsyncSession, token: str) -> None:
        result = await db.execute(
            select(EmailToken).where(
                EmailToken.token == token,
                EmailToken.token_type == "email_verification",
            )
        )
        email_token = result.scalar_one_or_none()

        if not email_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 인증 링크입니다.")
        if email_token.used_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용된 인증 링크입니다.")
        if email_token.expires_at < datetime.now(UTC).replace(tzinfo=None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="만료된 인증 링크입니다.")

        user_result = await db.execute(select(User).where(User.id == email_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 인증 링크입니다.")

        user.is_verified = True
        email_token.used_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

    # ── 인증 메일 재발송 ──────────────────────────
    async def resend_verification(self, db: AsyncSession, current_user: User) -> None:
        if current_user.is_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 인증된 이메일입니다.")
        if current_user.auth_provider != "local":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="소셜 로그인 계정은 이메일 인증이 필요하지 않습니다.")

        token_str = secrets.token_urlsafe(48)
        email_token = EmailToken(
            user_id=current_user.id,
            token=token_str,
            token_type="email_verification",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24),
        )
        db.add(email_token)
        await db.commit()

        await send_verification_email(
            to_email=current_user.email,
            to_name=current_user.nickname,
            token=token_str,
        )

    # ── 비밀번호 찾기 (재설정 메일 발송) ─────────
    async def forgot_password(self, db: AsyncSession, email: str) -> None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # 보안상 사용자 존재 여부를 노출하지 않음 — 항상 성공 응답
        if not user or user.auth_provider != "local":
            return

        token_str = secrets.token_urlsafe(48)
        email_token = EmailToken(
            user_id=user.id,
            token=token_str,
            token_type="password_reset",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        )
        db.add(email_token)
        await db.commit()

        await send_password_reset_email(
            to_email=user.email,
            to_name=user.nickname,
            token=token_str,
        )

    # ── 비밀번호 재설정 ───────────────────────────
    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None:
        result = await db.execute(
            select(EmailToken).where(
                EmailToken.token == token,
                EmailToken.token_type == "password_reset",
            )
        )
        email_token = result.scalar_one_or_none()

        if not email_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 링크입니다.")
        if email_token.used_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용된 링크입니다.")
        if email_token.expires_at < datetime.now(UTC).replace(tzinfo=None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="만료된 링크입니다. 다시 요청해 주세요.")

        user_result = await db.execute(select(User).where(User.id == email_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 링크입니다.")

        user.password_hash = hash_password(new_password)
        email_token.used_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

    # ── 로그인 ───────────────────────────────────
    async def login(self, db: AsyncSession, username: str, password: str) -> tuple[User, str]:
        result = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            )

        # 마지막 로그인 시각 갱신
        user.last_login_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)

        token = create_access_token(str(user.id))
        return user, token
