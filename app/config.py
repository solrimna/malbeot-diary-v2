from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database (환경별로 .env에서 분리)
    DATABASE_URL: str = "sqlite+aiosqlite:///./malbeot.db"
    USE_REDIS: bool = False  # 로컬은 False, EC2는 True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Azure Speech
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "koreacentral"

    # Web Push
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CLAIMS_SUB: str = "mailto:test@example.com"

    # Brevo (이메일 인증 & 비밀번호 재설정)
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "noreply@haru-commit.com"
    BREVO_SENDER_NAME: str = "하루.commit()"
    FRONTEND_BASE_URL: str = "https://haru-commit.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
