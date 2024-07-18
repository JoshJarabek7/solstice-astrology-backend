import httpx
import pytest
from fastapi import status

BASE_URL = "http://localhost:8000"  # Change this to your FastAPI server URL


@pytest.fixture(scope="session")
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        yield client


@pytest.fixture(scope="session")
async def jwt_token(client: httpx.AsyncClient):
    response = await client.post("/api/dev/user")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    return data["access_token"], data["user_id"]


@pytest.fixture(scope="session")
async def jwt_token_2(client: httpx.AsyncClient):
    response = await client.post("/api/dev/user")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    return data["access_token"], data["user_id"]


@pytest.fixture(scope="session")
async def headers(jwt_token: tuple[str, str]):
    token, _ = jwt_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
async def headers_2(jwt_token_2: tuple[str, str]):
    token, _ = jwt_token_2
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
async def post_id(client: httpx.AsyncClient, headers: dict[str, str]):
    response = await client.post(
        "/api/post",
        json={"content": "Test Post", "post_type": "general"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    return data["post_id"]


@pytest.fixture(scope="session")
async def post_id_2(client: httpx.AsyncClient, headers_2: dict[str, str]):
    response = await client.post(
        "/api/post",
        json={"content": "Test Post 2", "post_type": "general"},
        headers=headers_2,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    return data["post_id"]


@pytest.mark.asyncio()
async def test_create_user(client: httpx.AsyncClient):
    response = await client.post("/api/dev/user")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "user_id" in data


@pytest.mark.asyncio()
async def test_get_user_profile(client: httpx.AsyncClient, headers: dict[str, str]):
    response = await client.get("/api/user/profile/{user_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "user" in data


@pytest.mark.asyncio()
async def test_create_post(client: httpx.AsyncClient, headers: dict[str, str]):
    response = await client.post(
        "/api/post",
        json={"content": "Test Post", "post_type": "general"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "post_id" in data


@pytest.mark.asyncio()
async def test_get_post(client: httpx.AsyncClient, headers: dict[str, str], post_id: str):
    response = await client.get(f"/api/post/{post_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["post_id"] == post_id


@pytest.mark.asyncio()
async def test_like_post(client: httpx.AsyncClient, headers: dict[str, str], post_id: str):
    response = await client.post(f"/api/post/like/{post_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True


@pytest.mark.asyncio()
async def test_get_feed(client: httpx.AsyncClient, headers: dict[str, str]):
    response = await client.get("/api/feed/general", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "posts" in data


@pytest.mark.asyncio()
async def test_follow_user(client: httpx.AsyncClient, headers: dict[str, str], jwt_token_2: tuple[str, str]):
    _, user_id_2 = jwt_token_2
    response = await client.post(
        "/api/user/follow-requests",
        json={"user_id": user_id_2},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True


@pytest.mark.asyncio()
async def test_swipe_right(client: httpx.AsyncClient, headers: dict[str, str], jwt_token_2: tuple[str, str]):
    _, user_id_2 = jwt_token_2
    response = await client.post(
        "/api/dating/swipe",
        json={"swiped_right": True, "target_user_id": user_id_2},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True


@pytest.mark.asyncio()
async def test_delete_post(client: httpx.AsyncClient, headers: dict[str, str], post_id: str):
    response = await client.delete(f"/api/post/{post_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True


@pytest.mark.asyncio()
async def test_delete_user(client: httpx.AsyncClient, headers: dict[str, str]):
    response = await client.delete("/api/user", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "User account deleted successfully"
