import asyncio
from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import status

BASE_URL = "http://localhost:8000"  # Change this to your FastAPI server URL


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        yield client


class TestUser:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.access_token = None
        self.user_id = None

    async def create(self):
        response = await self.client.post("/api/dev/user")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        self.access_token = data["access_token"]
        self.user_id = data["user_id"]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def delete(self):
        response = await self.client.delete("/api/user", headers=self.headers)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User account deleted successfully"


class TestPost:
    def __init__(self, client: httpx.AsyncClient, user: TestUser):
        self.client = client
        self.user = user
        self.post_id = None

    async def create(self, content: str = "Test Post"):
        response = await self.client.post(
            "/api/post",
            json={"content": content, "post_type": "general"},
            headers=self.user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["successful"] is True
        self.post_id = data["post_id"]

    async def delete(self):
        response = await self.client.delete(f"/api/post/{self.post_id}", headers=self.user.headers)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["successful"] is True

@pytest.fixture(scope="session")
async def user_1(client: httpx.AsyncClient) -> AsyncGenerator[TestUser, None]:
    user = TestUser(client)
    await user.create()
    yield user
    await user.delete()


@pytest.fixture(scope="session")
async def user_2(client: httpx.AsyncClient) -> AsyncGenerator[TestUser, None]:
    user = TestUser(client)
    await user.create()
    yield user
    await user.delete()


@pytest.fixture(scope="session")
async def post_1(client: httpx.AsyncClient, user_1: TestUser) -> AsyncGenerator[TestPost, None]:
    post = TestPost(client, user_1)
    await post.create()
    yield post
    await post.delete()


@pytest.mark.asyncio()
async def test_create_user(client: httpx.AsyncClient) -> None:
    user = TestUser(client)
    await user.create()
    assert user.access_token is not None
    assert user.user_id is not None
    await user.delete()

@pytest.mark.asyncio()
async def test_get_user_profile(client: httpx.AsyncClient, user_1: TestUser) -> None:
    response = await client.get(f"/api/user/profile/{user_1.user_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "user" in data

@pytest.mark.asyncio()
async def test_get_post(client: httpx.AsyncClient, user_1: TestUser, post_1: TestPost) -> None:
    response = await client.get(f"/api/post/{post_1.post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["post_id"] == post_1.post_id


@pytest.mark.asyncio()
async def test_create_and_like_post(client: httpx.AsyncClient, user_1: TestUser):
    # Create a post
    response = await client.post(
        "/api/post",
        json={"content": "Test Post for Liking", "post_type": "general"},
        headers=user_1.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    post_data = response.json()
    post_id = post_data["post_id"]

    # Add a small delay to ensure the post is fully created
    await asyncio.sleep(0.5)

    # Verify the post exists
    response = await client.get(f"/api/post/{post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK

    # Like the post
    response = await client.post(f"/api/post/like/{post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True

@pytest.mark.asyncio()
async def test_delete_post(client: httpx.AsyncClient, user_1: TestUser):
    # Create a post specifically for deletion
    response = await client.post(
        "/api/post",
        json={"content": "Test Post for Deletion", "post_type": "general"},
        headers=user_1.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    post_data = response.json()
    post_id = post_data["post_id"]

    # Add a small delay to ensure the post is fully created
    await asyncio.sleep(0.5)

    # Verify the post exists before trying to delete it
    response = await client.get(f"/api/post/{post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK

    # Delete the post
    response = await client.delete(f"/api/post/{post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True

@pytest.mark.asyncio()
async def test_like_post(client: httpx.AsyncClient, user_1: TestUser, post_1: TestPost) -> None:
    response = await client.post(f"/api/post/like/{post_1.post_id}", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True

@pytest.mark.asyncio()
async def test_get_feed(client: httpx.AsyncClient, user_1: TestUser) -> None:
    response = await client.get("/api/feed/general", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "posts" in data

@pytest.mark.asyncio()
async def test_follow_user(client: httpx.AsyncClient, user_1: TestUser, user_2: TestUser) -> None:
    response = await client.post(
        "/api/user/follow-requests",
        json={"user_id": user_2.user_id},
        headers=user_1.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True

@pytest.mark.asyncio()
async def test_swipe_right(client: httpx.AsyncClient, user_1: TestUser, user_2: TestUser) -> None:
    response = await client.post(
        "/api/dating/swipe",
        json={"swiped_right": True, "requesting_user_id": user_1.user_id, "target_user_id": user_2.user_id},
        headers=user_1.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["successful"] is True

# @pytest.mark.asyncio()
# async def test_delete_post(client: httpx.AsyncClient, user_1: TestUser, post_1: TestPost) -> None:
#     response = await client.delete(f"/api/post/{post_1.post_id}", headers=user_1.headers)
#     assert response.status_code == status.HTTP_200_OK
#     data = response.json()
#     assert data["successful"] is True

@pytest.mark.asyncio()
async def test_delete_user(client: httpx.AsyncClient, user_1: TestUser) -> None:
    response = await client.delete("/api/user", headers=user_1.headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "User account deleted successfully"
