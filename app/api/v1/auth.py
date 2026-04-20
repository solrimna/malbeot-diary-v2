from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserLogin,
)
from app.services.auth_service import AuthService

router = APIRouter()
auth_svc = AuthService()


# ── POST /auth/register ─ 회원가입 ───────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_svc.register(db, body)
    return user


# ── POST /auth/login ─ 로그인 (JWT 발급) ─────────
@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    user, token = await auth_svc.login(db, body.username, body.password)
    return TokenResponse(access_token=token, user=user)


# ── POST /auth/logout ─ 로그아웃 ─────────────────
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # JWT는 stateless이므로 클라이언트에서 토큰 삭제로 처리
    return


# ── GET /auth/verify-email ─ 이메일 인증 완료 ────
@router.get("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    await auth_svc.verify_email(db, token)
    settings = get_settings()
    # 인증 완료 후 로그인 페이지로 리다이렉트
    return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/login.html?verified=true")


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_svc.resend_verification(db, current_user)
    return {"message": "인증 메일을 발송했습니다."}

# ── POST /auth/forgot-password ─ 재설정 메일 발송
@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await auth_svc.forgot_password(db, body.email)
    return {"message": "입력하신 이메일로 비밀번호 재설정 링크를 발송했습니다."}


# ── POST /auth/reset-password ─ 비밀번호 재설정 ─
@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await auth_svc.reset_password(db, body.token, body.new_password)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}
