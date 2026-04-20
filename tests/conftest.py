import app.models  # noqa: F401 — Base.metadata에 모든 테이블 등록
import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool
from unittest.mock import AsyncMock, patch

from app.services.gpt_service import GPTService

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


async def _mock_stream_feedback(self, **kwargs):
    """GPTService.stream_feedback 모킹 — 즉시 더미 피드백 반환"""
    yield "테스트 피드백입니다."


@pytest.fixture(scope="session")
async def engine():
    """엔진을 pytest-asyncio 루프 안에서 생성 (루프 충돌 방지)"""
    if "sqlite" in TEST_DB_URL:
        eng = create_async_engine(
            TEST_DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        eng = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_db(engine):
    from app.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def clean_tables(engine):
    """각 테스트 전 모든 데이터 초기화"""
    from app.database import Base
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db, engine):
    from app.database import get_db
    from app.main import app

    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with (
        patch("app.main.engine", engine),
        patch("app.services.alarm_scheduler.start_scheduler"),
        patch("app.services.alarm_scheduler.stop_scheduler"),
        patch.object(GPTService, "stream_feedback", _mock_stream_feedback),
        patch("app.services.gpt_service.gpt_service.generate_hashtags", AsyncMock(return_value=[])),
        patch("app.services.gpt_service.gpt_service.generate_summary", AsyncMock(return_value=None)),
        patch("app.services.email_service.send_verification_email", AsyncMock()),
        patch("app.services.email_service.send_password_reset_email", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client):
    """회원가입 + 로그인 후 인증 헤더 반환"""
    await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpass1",
        "nickname": "테스터",
    })
    res = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass1",
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
