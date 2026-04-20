"""Brevo 트랜잭션 메일 서비스.

담당:
  - 이메일 인증 매직 링크 발송
  - 비밀번호 재설정 링크 발송
"""
import html
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def _send_email(*, to_email: str, to_name: str, subject: str, html_content: str) -> None:
    settings = get_settings()

    payload = {
        "sender": {
            "email": settings.BREVO_SENDER_EMAIL,
            "name": settings.BREVO_SENDER_NAME,
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.BREVO_API_KEY,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(BREVO_API_URL, json=payload, headers=headers)

    if response.status_code not in (200, 201):
        logger.error("Brevo 메일 발송 실패: %s %s", response.status_code, response.text)
        raise RuntimeError(f"이메일 발송 실패 (status={response.status_code})")

    logger.info("메일 발송 완료: %s → %s", subject, to_email)


async def send_verification_email(*, to_email: str, to_name: str, token: str) -> None:
    """회원가입 이메일 인증 매직 링크 발송."""
    settings = get_settings()
    verify_url = f"{settings.FRONTEND_BASE_URL}/api/v1/auth/verify-email?token={token}"
    safe_name = html.escape(to_name)

    html_content = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #4f46e5;">하루.commit() 이메일 인증</h2>
      <p>안녕하세요, <strong>{safe_name}</strong>님!</p>
      <p>아래 버튼을 클릭하면 이메일 인증이 완료됩니다.<br>링크는 <strong>24시간</strong> 동안 유효합니다.</p>
      <a href="{verify_url}"
         style="display:inline-block; padding:12px 24px; background:#4f46e5;
                color:#fff; border-radius:8px; text-decoration:none; font-weight:bold;">
        이메일 인증하기
      </a>
      <p style="margin-top:24px; color:#888; font-size:12px;">
        본인이 요청하지 않았다면 이 메일을 무시하세요.
      </p>
    </div>
    """

    await _send_email(
        to_email=to_email,
        to_name=to_name,
        subject="[하루.commit()] 이메일 인증을 완료해 주세요",
        html_content=html_content,
    )


async def send_password_reset_email(*, to_email: str, to_name: str, token: str) -> None:
    """비밀번호 재설정 링크 발송."""
    settings = get_settings()
    reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password.html?token={token}"
    safe_name = html.escape(to_name)

    html_content = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #4f46e5;">하루.commit() 비밀번호 재설정</h2>
      <p>안녕하세요, <strong>{safe_name}</strong>님!</p>
      <p>아래 버튼을 클릭하면 새 비밀번호를 설정할 수 있습니다.<br>링크는 <strong>1시간</strong> 동안 유효하며 1회만 사용 가능합니다.</p>
      <a href="{reset_url}"
         style="display:inline-block; padding:12px 24px; background:#4f46e5;
                color:#fff; border-radius:8px; text-decoration:none; font-weight:bold;">
        비밀번호 재설정하기
      </a>
      <p style="margin-top:24px; color:#888; font-size:12px;">
        본인이 요청하지 않았다면 이 메일을 무시하세요. 링크는 곧 만료됩니다.
      </p>
    </div>
    """

    await _send_email(
        to_email=to_email,
        to_name=to_name,
        subject="[하루.commit()] 비밀번호 재설정 안내",
        html_content=html_content,
    )
