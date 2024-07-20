import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_mock
from fastapi import HTTPException

from app.users.db import (check_username_availability, create_dev_user_db,
                          delete_user_db, get_muted_users, get_user_profile,
                          mute_user, update_user_db)
from app.users.schemas import (BasicUserResponse, CreateUserResponse,
                               MutedUsersResponse, UpdateUserRequest,
                               UserProfileResponse)

user1_id = os.getenv("TEST_USER_1_ID")
user2_id = os.getenv("TEST_USER_2_ID")
user1_apple_id = os.getenv("TEST_USER_1_APPLE_ID")
user2_apple_id = os.getenv("TEST_USER_2_APPLE_ID")

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture()
def mock_neo4j_session(mocker: pytest_mock.MockerFixture):
    session = mocker.patch('app.shared.neo4j.driver.session', new_callable=AsyncMock)
    return session
@pytest.mark.asyncio
async def test_get_user_profile(mock_neo4j_session: AsyncMock):
    # Test case when no user is found
    mock_neo4j_session.return_value.run.return_value.single.return_value = None
    response = await get_user_profile("requesting_user_id", "target_user_id")
    assert response is None

    # Test case with mock data
    mock_data = {
        "user": {
            "user_id": "user1",
            "apple_id": "apple_id",
            "email": "test@example.com",
            "username": "testuser",
            "display_name": "Test User",
            "profile_photo": "photo_url",
            "header_photo": "header_url",
            "account_private": False,
            "dating_active": True,
            "following_count": 10,
            "followers_count": 20,
            "profile_song": "song_url",
            "created_at": datetime.now(UTC).isoformat(),
            "last_login": datetime.now(UTC).isoformat(),
        },
        "posts": [],
        "follows_user": True,
        "has_swiped_right": False,
        "has_swiped_left": False,
        "is_private": False,
    }
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    response = await get_user_profile("requesting_user_id", "target_user_id")
    assert isinstance(response, UserProfileResponse)
    assert response.user.user_id == "user1"

@pytest.mark.asyncio
async def test_create_dev_user_db(mock_neo4j_session: AsyncMock):
    mock_data = {
        "user": {
            "user_id": "user1",
            "apple_id": "apple_id",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "display_name": "Test User",
            "created_at": datetime.now(UTC).isoformat(),
            "last_login": datetime.now(UTC).isoformat(),
        }
    }
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    response = await create_dev_user_db("user1", "apple_id", "test@example.com", "Test", "User")
    assert isinstance(response, CreateUserResponse)
    assert response.user_id == "user1"

@pytest.mark.asyncio
async def test_update_user_db(mock_neo4j_session: AsyncMock):
    mock_data = {
        "user": {
            "user_id": "user1",
            "apple_id": "apple_id",
            "email": "test@example.com",
            "first_name": "Updated",
            "last_name": "User",
            "created_at": datetime.now(UTC).isoformat(),
            "last_login": datetime.now(UTC).isoformat(),
        }
    }
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    user_updates = UpdateUserRequest.model_validate({"first_name": "Updated"})
    response = await update_user_db("user1", user_updates)
    assert isinstance(response, BasicUserResponse)
    assert response.first_name == "Updated"

@pytest.mark.asyncio
async def test_delete_user_db(mock_neo4j_session: AsyncMock):
    mock_data = {"deleted_count": 1}
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    await delete_user_db("user1")
    mock_neo4j_session.return_value.run.assert_called_once()

    # Test case when no user is deleted
    mock_data = {"deleted_count": 0}
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    with pytest.raises(HTTPException):
        await delete_user_db("non_existent_user")

@pytest.mark.asyncio
async def test_check_username_availability(mock_neo4j_session: AsyncMock):
    # Test when username is available
    mock_neo4j_session.return_value.run.return_value.single.return_value = None
    available = await check_username_availability("new_username")
    assert available is True

    # Test when username is taken
    mock_neo4j_session.return_value.run.return_value.single.return_value = {"username": "existing_username"}
    available = await check_username_availability("existing_username")
    assert available is False

@pytest.mark.asyncio
async def test_get_muted_users(mock_neo4j_session: AsyncMock):
    mock_data = {
        "muted_list": [
            {
                "user_id": "user2",
                "profile_photo": "photo_url",
                "username": "muteduser",
                "display_name": "Muted User",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    }
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    response = await get_muted_users("user1")
    assert isinstance(response, MutedUsersResponse)
    assert len(response.muted_list) == 1
    assert response.muted_list[0].user_id == "user2"

    # Test case when no muted users are found
    mock_neo4j_session.return_value.run.return_value.single.return_value = None
    with pytest.raises(HTTPException):
        await get_muted_users("user1")

@pytest.mark.asyncio
async def test_mute_user(mock_neo4j_session: AsyncMock):
    mock_data = {
        "r": {
            "created_at": datetime.now(UTC).isoformat(),
        }
    }
    mock_neo4j_session.return_value.run.return_value.single.return_value = mock_data
    response = await mute_user("user1", "user2")
    assert response["successful"] is True
    assert response["muted_user_id"] == "user2"

    # Test case when muting fails
    mock_neo4j_session.return_value.run.return_value.single.return_value = None
    response = await mute_user("user1", "user2")
    assert response["successful"] is False