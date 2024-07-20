from datetime import datetime

from fastapi import Depends, HTTPException, Query, status
from faststream.kafka.fastapi import KafkaRouter

from app.shared.auth import VerifiedUser, get_current_user, oauth2_scheme, refresh_user
from app.shared.schemas import WasSuccessfulResponse
from app.users.db import (
    block_user,
    check_username_availability,
    create_user_db,
    delete_follow_request,
    delete_user_db,
    get_block_list,
    get_follow_recommendations,
    get_follow_requests,
    get_followers,
    get_following,
    get_muted_users,
    get_user_profile,
    mute_user,
    send_follow_request,
    unblock_user,
    unfollow_user,
    unmute_user,
    update_user_db,
)
from app.users.schemas import (
    BasicUserResponse,
    BlockedUsersResponse,
    BlockUserRequest,
    CreateUserResponse,
    FollowingResponse,
    FollowRequestResponse,
    GetFollowersResponse,
    GetFollowRecommendationsResponse,
    MutedUsersResponse,
    MuteUserRequest,
    RefreshTokenRequest,
    SendFollowReqRequest,
    TokenResponse,
    UpdateUserRequest,
    UsernameCheckResponse,
    UserProfileResponse,
)

router = KafkaRouter()

@router.post("/api/user", response_model=CreateUserResponse)
async def create_user_route(
    apple_token: str = Depends(oauth2_scheme),
) -> CreateUserResponse:
    """Create a new user after successful Apple authentication.

    Args:
        apple_token (str): The OAuth2 token received from Apple.

    Returns:
        CreateUserResponse: The response containing the created user details.
    """
    return await create_user_db(apple_token)

@router.put("/api/user", response_model=BasicUserResponse)
async def update_user_route(
    user_updates: UpdateUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BasicUserResponse:
    """Updates user information.

    Args:
        user_updates (UpdateUserRequest): The request body containing user updates.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        BasicUserResponse: The updated user information.
    """
    return await update_user_db(verified_user.user_id, user_updates)

@router.delete("/api/user", response_model=None)
async def delete_user_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """Delete the authenticated user's account.

    Args:
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or deletion fails.

    Returns:
        None: None
    """
    return await delete_user_db(verified_user.user_id)

@router.get("/api/user/username-availability/{username}", response_model=UsernameCheckResponse)
async def check_username_route(
    username: str,
) -> UsernameCheckResponse:
    """Check if a username is available.

    Args:
        username (str): The username to check.

    Returns:
        UsernameCheckResponse: The response containing the availability status.
    """
    res = await check_username_availability(username)
    return UsernameCheckResponse(username_exists=res)


@router.get("/api/user/profile/{target_user_id}", response_model=UserProfileResponse | None)
async def get_user_route(
    target_user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> UserProfileResponse | None:
    """Get a user's profile.

    Args:
        target_user_id (str): The ID of the user to get the profile for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of follows to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        UserProfileResponse | None: The user's profile or None if the user is not found.
    """
    return await get_user_profile(
        requesting_user_id = verified_user.user_id,
        target_user_id=target_user_id,
        cursor=cursor,
        limit=limit,
        )


@router.post("/api/user/refresh", response_model=TokenResponse)
async def refresh_user_route(token_data: RefreshTokenRequest) -> TokenResponse:
    """Refresh the user's token.

    Args:
        token_data (RefreshTokenRequest): The request containing the refresh token.

    Returns:
        TokenResponse: The response containing the access token and refresh token.
    """
    return await refresh_user(token_data)


@router.get("/api/user/mute", response_model=MutedUsersResponse)
async def get_muted_users_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> MutedUsersResponse:
    """Get a list of muted users.

    Args:
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        MutedUsersResponse: The list of muted users.
    """
    return await get_muted_users(verified_user.user_id)

@router.post("/api/user/mute", response_model=WasSuccessfulResponse)
async def mute_user_route(
    request: MuteUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Mute a user.

    Args:
        request (MuteUserRequest): The request containing the user ID to mute.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was muted.
    """
    res = await mute_user(verified_user.user_id, request.user_id)
    if res["successful"]:
        return WasSuccessfulResponse(successful=True)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found.",
    )

@router.delete("/api/user/mute/{user_id}", response_model=WasSuccessfulResponse)
async def unmute_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unmute a user.

    Args:
        user_id (str): The user ID to unmute.
        verified_user: The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was unmuted.
    """
    res = await unmute_user(verified_user.user_id, user_id)
    return WasSuccessfulResponse(successful=res)

@router.get("/api/user/follows/{user_id}", response_model=FollowingResponse)
async def get_following_route(
    user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> FollowingResponse:
    return await get_following(
        verified_user.user_id,
        user_id,
        cursor,
        limit,
    )

@router.delete("/api/user/follows/{user_id}", response_model=WasSuccessfulResponse)
async def unfollow_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unfollow a user.

    Args:
        user_id (str): The user ID to unfollow.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was unfollowed.
    """
    res = await unfollow_user(verified_user.user_id, user_id)
    return WasSuccessfulResponse(successful=res)


@router.get("/api/user/follow-requests", response_model=FollowRequestResponse)
async def get_follow_requests_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> FollowRequestResponse:
    """Get a list of follow requests.

    Args:
        verified_user (VerifiedUser): The user making the request.

    Returns:
        FollowRequestResponse: The list of follow requests.
    """
    return await get_follow_requests(verified_user.user_id)

@router.post("/api/user/follow-requests", response_model=WasSuccessfulResponse)
async def send_follow_request_route(
    request: SendFollowReqRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Send a follow request.

    Args:
        request (SendFollowReqRequest): The request containing the user ID to send the follow request to.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the follow request was sent.
    """
    res = await send_follow_request(verified_user.user_id, request.user_id)
    return WasSuccessfulResponse(successful=res)


@router.get("/api/user/followers/{user_id}", response_model=GetFollowersResponse)
async def get_followers_route(
    user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> GetFollowersResponse:
    return await get_followers(verified_user.user_id, user_id, cursor, limit)


@router.delete("/api/user/follow-requests/{request_id}", response_model=WasSuccessfulResponse)
async def delete_follow_request_route(
    request_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete/deny a follow request received from a user.

    Args:
        request_id (str): The ID of the follow request to delete.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the follow request was deleted.
    """
    res = await delete_follow_request(verified_user.user_id, request_id)
    return WasSuccessfulResponse(successful=res)


@router.get("/api/user/recommendations", response_model=GetFollowRecommendationsResponse)
async def get_follow_recommendations_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> GetFollowRecommendationsResponse:
    """Get a list of users that the user may want to follow.

    Args:
        verified_user (VerifiedUser): The user making the request.

    Returns:
        GetFollowRecommendationsResponse: The list of users that the user may want to follow.
    """
    return await get_follow_recommendations(verified_user.user_id)


@router.get("/api/user/block", response_model=BlockedUsersResponse)
async def get_block_list_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BlockedUsersResponse:
    """Get a list of blocked users.

    Args:
        verified_user (VerifiedUser): The user making the request.

    Returns:
        BlockedUsersResponse: The list of blocked users.
    """
    return await get_block_list(verified_user.user_id)


@router.post("/api/user/block", response_model=WasSuccessfulResponse)
async def block_user_route(
    request: BlockUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Block a user.

    Args:
        request (BlockUserRequest): The request containing the user ID to block.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was blocked.
    """
    res = await block_user(verified_user.user_id, request.user_id)
    return WasSuccessfulResponse(successful=res)


@router.delete("/api/user/block/{user_id}", response_model=WasSuccessfulResponse)
async def unblock_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:

    res = await unblock_user(verified_user.user_id, user_id)
    return WasSuccessfulResponse(successful=res)


