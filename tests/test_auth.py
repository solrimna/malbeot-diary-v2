import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

USER = {"username": "testuser", "email": "testuser@example.com", "password": "testpass1", "nickname": "테스터"}


async def test_register(client):
    res = await client.post(REGISTER_URL, json=USER)
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == USER["username"]
    assert body["nickname"] == USER["nickname"]
    assert "password" not in body


async def test_register_duplicate(client):
    await client.post(REGISTER_URL, json=USER)
    res = await client.post(REGISTER_URL, json=USER)
    assert res.status_code == 409


async def test_login(client):
    await client.post(REGISTER_URL, json=USER)
    res = await client.post(LOGIN_URL, json={"username": USER["username"], "password": USER["password"]})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == USER["username"]


async def test_login_wrong_password(client):
    await client.post(REGISTER_URL, json=USER)
    res = await client.post(LOGIN_URL, json={"username": USER["username"], "password": "wrongpass"})
    assert res.status_code == 401


async def test_login_unknown_user(client):
    res = await client.post(LOGIN_URL, json={"username": "nobody", "password": "testpass1"})
    assert res.status_code == 401
