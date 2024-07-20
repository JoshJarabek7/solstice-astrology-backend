import asyncio
import sys

from dotenv import load_dotenv
from loguru import logger

from app.users.db import check_username_availability, create_dev_user_db, delete_user_db, get_user_profile, update_user_db
from app.users.schemas import UpdateUserRequest, UserProfileResponse

load_dotenv()

logger.add(sys.stderr, level="INFO")

TEST_USER_1_ID="05a23aa0-c8f8-422c-ae8b-abfeb7bea990"
TEST_USER_1_APPLE_ID="8e33e696-58f6-4937-b77a-e75eb31260b2"
TEST_USER_2_ID="73730b0d-7699-4550-81cc-d50d76c9dc3e"
TEST_USER_2_APPLE_ID="d3730646-407e-4a7e-9b87-dc28ef24957b"
async def main():
    """Create our users first
    """
    # Create users
    user_one = await create_dev_user_db(TEST_USER_1_ID, TEST_USER_1_APPLE_ID, "test@example.com", "Test", "User")
    user_two = await create_dev_user_db(TEST_USER_2_ID, TEST_USER_2_APPLE_ID, "test@example.com", "Test", "User")
    logger.info(f"User one created successfully: {user_one.user_id}")
    logger.info(f"User two created successfully: {user_two.user_id}")

    # Get user profiles to ensure they're created
    user_two_profile = await get_user_profile(user_one.user_id, user_two.user_id)
    logger.info(f"User two profile exists: {user_two_profile is not None}")
    logger.info(f"User two isinstance of UserProfileResponse: {isinstance(user_two_profile, UserProfileResponse)}")

    # Update user one
    user_one_old_username = user_one.username
    user_one_updates = await update_user_db(user_one.user_id, UpdateUserRequest(
        username="newusername",
        first_name="New",
        last_name="User",
        account_active=True,
        account_private=True,
        dating_active=True,
    ))
    logger.info(f"User one's username was updated: {user_one_updates.username !=  user_one_old_username and user_one_updates.username == 'newusername'}")

    # Create user three
    user3 = await create_dev_user_db("user3", "user3appleid", "user3@example.com", "User3", "User")
    user3_profile = await get_user_profile(user_one.user_id, user3.user_id)
    logger.info(f"User three successfully created: {isinstance(user3_profile, UserProfileResponse)}")

    # Check if user3newusername is available
    is_available = await check_username_availability("user3newusername")
    logger.info(f"User three's username is available: {is_available}")

    # Update username
    await update_user_db(user3.user_id, UpdateUserRequest(
        username="user3newusername",
    ))

    # Confirm username is no longer available
    is_available = await check_username_availability("user3newusername")
    logger.info(f"User three's username is no longer available: {not is_available}")

    # Delete user three
    await delete_user_db("user3")
    user3_exists = await get_user_profile(user_one.user_id, user3.user_id)
    logger.info(f"User three deleted successfully: {user3_exists is None}")

    # User one should follow user two


    """
    Create our posts
    """

    """
    Create our dating swipes
    """

    """
    Create our notifications
    """

if __name__ == "__main__":
    asyncio.run(main())
