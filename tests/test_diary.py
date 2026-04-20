import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

DIARIES_URL = "/api/v1/diaries/"

DIARY_DATA = {
    "content": "오늘은 정말 좋은 하루였다.",
    "diary_date": "2026-04-11",
    "emotion": "행복",
    "weather": "맑음",
    "hashtags": [],
}


@pytest.fixture
async def diary_id(client, auth_headers):
    res = await client.post(DIARIES_URL, json=DIARY_DATA, headers=auth_headers)
    return res.json()["id"]


async def test_create_diary(client, auth_headers):
    res = await client.post(DIARIES_URL, json=DIARY_DATA, headers=auth_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["content"] == DIARY_DATA["content"]
    assert body["emotion"] == DIARY_DATA["emotion"]
    assert body["diary_date"] == DIARY_DATA["diary_date"]


async def test_list_diaries(client, auth_headers, diary_id):
    res = await client.get(DIARIES_URL, headers=auth_headers)
    assert res.status_code == 200
    ids = [d["id"] for d in res.json()]
    assert diary_id in ids


async def test_get_diary(client, auth_headers, diary_id):
    res = await client.get(f"{DIARIES_URL}{diary_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == diary_id


async def test_update_diary(client, auth_headers, diary_id):
    res = await client.patch(
        f"{DIARIES_URL}{diary_id}",
        json={"content": "수정된 내용입니다.", "emotion": "평온"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "수정된 내용입니다."
    assert body["emotion"] == "평온"


async def test_delete_diary(client, auth_headers, diary_id):
    res = await client.delete(f"{DIARIES_URL}{diary_id}", headers=auth_headers)
    assert res.status_code == 204

    res = await client.get(f"{DIARIES_URL}{diary_id}", headers=auth_headers)
    assert res.status_code == 404


async def test_diary_isolated_between_users(client, auth_headers, diary_id):
    """다른 사용자는 내 일기를 조회할 수 없음"""
    await client.post("/api/v1/auth/register", json={
        "username": "otheruser",
        "email": "otheruser@example.com",
        "password": "testpass2",
        "nickname": "다른유저",
    })
    res = await client.post("/api/v1/auth/login", json={
        "username": "otheruser",
        "password": "testpass2",
    })
    other_headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    res = await client.get(f"{DIARIES_URL}{diary_id}", headers=other_headers)
    assert res.status_code == 404


async def test_unauthenticated_request(client):
    res = await client.get(DIARIES_URL)
    assert res.status_code in (401, 403)
