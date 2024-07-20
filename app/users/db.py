from datetime import UTC, datetime, timedelta
from typing import Any, LiteralString, cast
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, status
from loguru import logger
from pydantic import EmailStr

from app.posts.schemas import PostResponse
from app.shared.auth import create_dev_jwt, exchange_auth_code, oauth2_scheme, verify_id_token
from app.shared.neo4j import driver
from app.shared.settings import settings_model
from app.users.schemas import (
    BasicUserResponse,
    BlockedUsersResponse,
    CreateUserResponse,
    FollowingResponse,
    FollowRequestResponse,
    GetFollowersResponse,
    GetFollowRecommendationsResponse,
    MutedUsersResponse,
    SimpleUserResponse,
    UpdateUserRequest,
    UserProfileResponse,
)


async def get_user_profile(requesting_user_id: str, target_user_id: str, cursor: datetime | None = None, limit: int = 100) -> UserProfileResponse | None:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})
    MATCH (target_user:User {user_id: $target_user_id})

    // Check if either user has blocked the other
    OPTIONAL MATCH (requesting_user)-[:BLOCKS]-(target_user)
    WITH requesting_user, target_user, COUNT(DISTINCT target_user) AS block_count

    // Check if requesting user follows the target user
    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(target_user)
    WITH requesting_user, target_user, block_count, COUNT(DISTINCT target_user) AS following_count

    // Check if requesting user has swiped on the target user
    OPTIONAL MATCH (requesting_user)-[swiped_right:SWIPED_RIGHT]->(target_user)
    OPTIONAL MATCH (requesting_user)-[swiped_left:SWIPED_LEFT]->(target_user)

    WHERE block_count = 0

    // Fetch posts created by the target user with pagination
    OPTIONAL MATCH (target_user)-[p:POSTED]->(post:Post)
    WHERE (target_user.account_private = FALSE OR following_count > 0) AND p.created_at < $cursor
    WITH requesting_user, target_user, post, p, following_count, target_user.account_private AS account_private, swiped_right, swiped_left

    // Handle QUOTED and REPLIED relationships
    OPTIONAL MATCH (post)-[q:QUOTED]->(quoted_post:Post)<-[:POSTED]-(quoted_poster:User)
    OPTIONAL MATCH (post)-[r:REPLIED]->(replied_post:Post)<-[:POSTED]-(replied_poster:User)

    // Handle REPOSTED relationship
    OPTIONAL MATCH (target_user)-[rp:REPOSTED]->(reposted_post:Post)<-[:POSTED]-(reposted_poster:User)
    WHERE (target_user.account_private = FALSE OR following_count > 0) AND rp.created_at < $cursor

    WITH requesting_user, target_user, post, p, q, r, rp,
         quoted_post, replied_post, reposted_post,
         quoted_poster, replied_poster, reposted_poster,
         following_count, account_private, swiped_right, swiped_left
    ORDER BY COALESCE(p.created_at, rp.created_at) DESC
    LIMIT $limit + 1

    // Check privacy for quoted and replied posts
    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(quoted_poster)
    WITH *, COUNT(quoted_poster) > 0 AS follows_quoted_poster

    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(replied_poster)
    WITH *, COUNT(replied_poster) > 0 AS follows_replied_poster

    RETURN target_user {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .header_photo,
        .account_private,
        .dating_active,
        .following_count,
        .followers_count,
        .profile_song,
        .apple_id,
        .email
    } AS user,
    collect({
        post_id: CASE WHEN post IS NOT NULL THEN post.post_id ELSE reposted_post.post_id END,
        content: CASE WHEN post IS NOT NULL THEN post.content ELSE reposted_post.content END,
        created_at: CASE WHEN p IS NOT NULL THEN p.created_at ELSE rp.created_at END,
        post_type: CASE
            WHEN p IS NOT NULL THEN 'POSTED'
            WHEN rp IS NOT NULL THEN 'REPOSTED'
            ELSE NULL
        END,
        is_video: CASE WHEN post IS NOT NULL THEN post.is_video ELSE reposted_post.is_video END,
        video_url: CASE WHEN post IS NOT NULL THEN post.video_url ELSE reposted_post.video_url END,
        video_length: CASE WHEN post IS NOT NULL THEN post.video_length ELSE reposted_post.video_length END,
        like_count: CASE WHEN post IS NOT NULL THEN post.like_count ELSE reposted_post.like_count END,
        view_count: CASE WHEN post IS NOT NULL THEN post.view_count ELSE reposted_post.view_count END,
        attachments: CASE WHEN post IS NOT NULL THEN post.attachments ELSE reposted_post.attachments END,
        quote_count: CASE WHEN post IS NOT NULL THEN post.quote_count ELSE reposted_post.quote_count END,
        reply_count: CASE WHEN post IS NOT NULL THEN post.reply_count ELSE reposted_post.reply_count END,
        repost_count: CASE WHEN post IS NOT NULL THEN post.repost_count ELSE reposted_post.repost_count END,
        bookmark_count: CASE WHEN post IS NOT NULL THEN post.bookmark_count ELSE reposted_post.bookmark_count END,
        mentions: CASE WHEN post IS NOT NULL THEN post.mentions ELSE reposted_post.mentions END,
        hashtags: CASE WHEN post IS NOT NULL THEN post.hashtags ELSE reposted_post.hashtags END,
        poster: CASE
            WHEN p IS NOT NULL THEN target_user {.user_id, .username, .display_name, .profile_photo}
            WHEN rp IS NOT NULL THEN reposted_poster {.user_id, .username, .display_name, .profile_photo}
            ELSE NULL
        END,
        quoted_post: CASE WHEN q IS NOT NULL
            THEN quoted_post {
                .post_id,
                .content,
                .created_at,
                poster: quoted_poster {.user_id, .username, .display_name, .profile_photo}
            }
            ELSE NULL
        END,
        replied_post: CASE WHEN r IS NOT NULL
            THEN replied_post {
                .post_id,
                .content,
                .created_at,
                poster: replied_poster {.user_id, .username, .display_name, .profile_photo}
            }
            ELSE NULL
        END,
        quoted_post_private: CASE WHEN q IS NOT NULL THEN quoted_poster.account_private AND NOT follows_quoted_poster ELSE NULL END,
        replied_post_private: CASE WHEN r IS NOT NULL THEN replied_poster.account_private AND NOT follows_replied_poster ELSE NULL END
    }) AS posts,
    following_count > 0 AS follows_user,
    swiped_right IS NOT NULL AS has_swiped_right,
    swiped_left IS NOT NULL AS has_swiped_left,
    (target_user.account_private AND following_count = 0) AS is_private
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        record = await result.single()

        if not record:
            return None

        user_data = record["user"]
        posts_data: list[dict[str, Any]] = record["posts"]
        follows_user = record["follows_user"]
        has_swiped_right = record["has_swiped_right"]
        has_swiped_left = record["has_swiped_left"]
        is_private = record["is_private"]

        user = BasicUserResponse(**user_data)
        posts: list[PostResponse] = []
        for post in posts_data[:limit]:
            post_data = {**post}
            if post["quoted_post"]:
                post_data["quoted_post"] = PostResponse(
                    **post["quoted_post"],
                    poster=SimpleUserResponse(**post["quoted_post"]["poster"]),
                    quoted_post=None,
                    replied_post=None,
                )
            if post["replied_post"]:
                post_data["replied_post"] = PostResponse(
                    **post["replied_post"],
                    poster=SimpleUserResponse(**post["replied_post"]["poster"]),
                    quoted_post=None,
                    replied_post=None,
                )
            post_data["poster"] = SimpleUserResponse(**post["poster"])
            posts.append(PostResponse(**post_data))

        has_more = len(posts_data) > limit
        next_cursor = posts[-1].created_at if has_more else None

        return UserProfileResponse(
            user=user,
            posts=posts,
            follows_user=follows_user,
            has_swiped_right=has_swiped_right,
            has_swiped_left=has_swiped_left,
            has_more=has_more,
            next_cursor=next_cursor,
            is_private=is_private,
        )

async def create_dev_user_db(user_id: str, apple_id: str, email: EmailStr, first_name: str, last_name: str, account_active: bool = True, account_private: bool = False, dating_active: bool = True) -> CreateUserResponse:
    now = datetime.now(UTC)
    query = """
    MERGE (user:User {apple_id: $apple_id})
    ON CREATE SET
        user.user_id = $user_id,
        user.apple_id = $apple_id,
        user.email = $email,
        user.first_name = $first_name,
        user.last_name = $last_name,
        user.created_at = $created_at,
        user.last_login = $last_login,
        user.account_active = $account_active,
        user.account_private = $account_private,
        user.dating_active = $dating_active
    ON MATCH SET
        user.last_login = $last_login
    RETURN user
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "apple_id": apple_id,
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": now.isoformat(),
                "last_login": now.isoformat(),
                "account_active": account_active,
                "account_private": account_private,
                "dating_active": dating_active,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed.",
            )
        user_data = record["user"]
        access_token = create_dev_jwt(user_id)
        return CreateUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=cast(EmailStr, user_data["email"]),
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            username=user_data.get("username", None),
            display_name=user_data.get("display_name", None),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
            access_token=access_token,
            refresh_token=None,
        )

async def create_user_db(apple_token: str = Depends(oauth2_scheme)) -> CreateUserResponse:
    try:
        # Verify the id_token with Apple and get user info
        user_info = await verify_id_token(apple_token)
        # Exchange the authorization code for access and refresh tokens
        apple_token_response = await exchange_auth_code(apple_token, user_info["sub"])
    except HTTPException as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Apple token.",
        ) from err
    apple_id = user_info["sub"]
    email = user_info["email"]
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    apple_refresh_token = apple_token_response.refresh_token

    user_id = str(uuid4())
    token_id = str(uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=30)

    query = """
        MERGE (user:User {apple_id: $apple_id})
        ON CREATE SET
            user.user_id = $user_id,
            user.apple_id = $apple_id,
            user.email = $email,
            user.first_name = $first_name,
            user.last_name = $last_name,
            user.created_at = $created_at,
            user.last_login = $last_login
        ON MATCH SET
            user.last_login = $last_login
        WITH user
        CREATE (user)-[:HAS_REFRESH_TOKEN {
            token_id: $token_id,
            refresh_token: $apple_refresh_token,
            created_at: $created_at,
            expires_at: $expires_at
        }]->(token:Token)
        RETURN user, token
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "apple_id": apple_id,
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "apple_refresh_token": apple_refresh_token,
                "token_id": token_id,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_login": now.isoformat(),
            },
        )
        record = await result.single()
        logger.debug(f"Record for create user: {record}")
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed.",
            )
        user_data = record["user"]
        # Generate access token
        access_token = jwt.encode(
            {
                "sub": user_id,
                "exp": datetime.now(UTC) + timedelta(minutes=15),  # Access token expiry
                "user_id": user_id,
            },
            str(settings_model.jwt.private_key),
            algorithm="RS256",
        )
        return CreateUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=user_data["email"],
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            username=user_data.get("username", None),
            display_name=user_data.get("display_name", None),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
            access_token=access_token,
            refresh_token=apple_refresh_token,
        )


async def update_user_db(user_id: str, user_updates: UpdateUserRequest) -> BasicUserResponse:
    set_clauses: list[str] = []
    params = {
        "user_id": user_id,
    }

    for field, value in user_updates.model_dump(exclude_unset=True).items():
        set_clauses.append(f"user.{field} = ${field}")
        params[field] = value

    set_clause = ", ".join(set_clauses)

    query = cast(
        LiteralString,
        f"""
        MATCH (user:User {{user_id: $user_id}})
        SET {set_clause}
        RETURN user
        """,
    )

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record:
            logger.exception(f"User {user_id} not found or user {user_id} doesn't have permission to update it.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        user_data = record["user"]
        return BasicUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=user_data.get("email", None),
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            profile_photo=user_data.get("profile_photo", None),
            header_photo=user_data.get("header_photo", None),
            profile_song=user_data.get("profile_song", None),
            account_active=user_data.get("account_active", True),
            account_private=user_data.get("account_private", False),
            username=user_data.get("username", None),
            following_count=user_data.get("following_count", 0),
            followers_count=user_data.get("followers_count", 0),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
        )

async def delete_user_db(user_id: str) -> None:
    query = """
    MATCH (user:User {user_id: $user_id})
    DETACH DELETE user
    RETURN COUNT(user) AS deleted_count
    """

    async with driver.session() as session:
        result = await session.run(query, {"user_id": user_id})
        record = await result.single()
        logger.debug(f"Delete user query result: {record} for user {user_id}")
        if not record or record["deleted_count"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User deletion failed",
            )


async def check_username_availability(username: str) -> bool:
    query = """
    MATCH (user:User {username: $username})
    RETURN user.username AS username
    """

    async with driver.session() as session:
        result = await session.run(query, {"username": username})
        record = await result.single()
        if not record:
            return False
        return True

"""---------------- MUTES -----------------"""
async def get_muted_users(user_id: str) -> MutedUsersResponse:
    query = """
    MATCH (user:User {user_id: $user_id})-[r:MUTES]->(muted_user:User)
    RETURN muted_user.user_id AS user_id,
        muted_user.profile_photo AS profile_photo,
        muted_user.username AS username,
        muted_user.display_name AS display_name,
        r.created_at AS created_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No muted users found.",
            )
        return MutedUsersResponse(
            muted_list=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["muted_list"]
            ],
        )

async def mute_user(requesting_user_id: str, target_user_id: str) -> dict[str, str | bool]:
    query = """
    MATCH (user:User {user_id: $user_id})
    MERGE (user)-[r:MUTES {created_at: $created_at}]->(muted_user:User {user_id: $muted_user_id})
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": requesting_user_id,
                "muted_user_id": target_user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        return {
            "successful": record is not None,
            "muted_user_id": target_user_id,
        }

async def unmute_user(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})-[r:MUTES]->(muted_user:User {user_id: $muted_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "muted_user_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return True

"""---------------- FOLLOWS -----------------"""
async def get_following(requesting_user_id: str, target_user_id: str, cursor: datetime | None = None, limit: int = 100)-> FollowingResponse:
    cursor = cursor or datetime.now(UTC)

    # Skip privacy and block checks if the user is checking their own profile
    if requesting_user_id != target_user_id:
        # Check if the target user is private and if the requesting user follows them
        check_private_and_follows_query = """
        MATCH (target_user:User {user_id: $target_user_id})
        OPTIONAL MATCH (requesting_user:User {user_id: $requesting_user_id})-[:FOLLOWS]->(target_user)
        OPTIONAL MATCH (requesting_user)-[:BLOCKS]-(target_user)
        RETURN target_user.account_private AS is_private, COUNT(DISTINCT requesting_user) > 0 AS follows, COUNT(DISTINCT target_user) = 0 AS blocked
        """  # noqa: E501

        async with driver.session() as session:
            check_result = await session.run(
                check_private_and_follows_query,
                {
                    "target_user_id": target_user_id,
                    "requesting_user_id": requesting_user_id,
                },
            )
            check_data = await check_result.single()
            if not check_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )

            is_private = check_data["is_private"]
            follows = check_data["follows"]
            blocked = check_data["blocked"]

            if blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You have blocked this user.",
                )
            if is_private and not follows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User profile is private.",
                )

    # Query to fetch the follows with pagination and sorting
    fetch_follows_query = """
    MATCH (user:User {user_id: $user_id})-[:FOLLOWS]->(followed_user:User)
    WHERE followed_user.created_at < $cursor
    RETURN followed_user {
        .user_id,
        .profile_photo,
        .username,
        .display_name,
        .created_at
    } AS followed_user
    ORDER BY followed_user.created_at DESC
    LIMIT $limit + 1
    """

    async with driver.session() as session:
        fetch_result = await session.run(
            fetch_follows_query,
            {
                "user_id": target_user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        follows_data = await fetch_result.data()

        follows_list = [
            SimpleUserResponse(
                user_id=user["followed_user"]["user_id"],
                profile_photo=user["followed_user"].get("profile_photo"),
                username=user["followed_user"].get("username"),
                display_name=user["followed_user"].get("display_name"),
                created_at=datetime.fromisoformat(user["followed_user"]["created_at"]),
            )
            for user in follows_data[:limit]  # Only take up to the limit
        ]

        has_more = len(follows_data) > limit
        next_cursor = follows_data[limit - 1]["followed_user"]["created_at"] if has_more else None

    return FollowingResponse(
        user_follows=follows_list,
        has_more=has_more,
        next_cursor=next_cursor,
    )

async def unfollow_user(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})-[r:FOLLOWS]->(followed_user:User {user_id: $target_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return True

async def get_follow_requests(requesting_user_id: str) -> FollowRequestResponse:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})-[r:FOLLOW_REQUEST]->(followed_user:User)
    RETURN followed_user.user_id AS user_id,
        followed_user.profile_photo AS profile_photo,
        followed_user.username AS username,
        followed_user.display_name AS display_name,
        r.created_at AS created_at
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No follow requests found.",
            )
        return FollowRequestResponse(
            user_follow_requests=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["user_follow_requests"]
            ],
        )


async def send_follow_request(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})
    MATCH (target_user:User {user_id: $target_user_id})
    OPTIONAL MATCH (requesting_user)-[:BLOCKS]->(target_user)
    OPTIONAL MATCH (target_user)-[:BLOCKS]->(requesting_user)
    WITH requesting_user, target_user, COUNT(DISTINCT requesting_user) AS requesting_user_blocks, COUNT(DISTINCT target_user) AS target_user_blocks
    WHERE requesting_user_blocks = 0 AND target_user_blocks = 0
    RETURN target_user.account_private AS is_private
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
            },
        )
        record = await result.single()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or blocked.",
            )

        is_private = record["is_private"]

        if is_private:
            relationship_query = """
            MATCH (requesting_user:User {user_id: $requesting_user_id})
            MATCH (target_user:User {user_id: $target_user_id})
            MERGE (requesting_user)-[r:FOLLOW_REQUEST {created_at: $created_at}]->(target_user)
            RETURN r
            """
        else:
            relationship_query = """
            MATCH (requesting_user:User {user_id: $requesting_user_id})
            MATCH (target_user:User {user_id: $target_user_id})
            MERGE (requesting_user)-[r:FOLLOWS {created_at: $created_at}]->(target_user)
            RETURN r
            """

        result = await session.run(
            relationship_query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow request.",
            )
        return True

async def delete_follow_request(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})-[r:FOLLOW_REQUEST]->(target_user:User {user_id: $target_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or follow request not found.",
            )
        return True



async def get_followers(requesting_user_id: str, target_user_id: str, cursor: datetime | None = None, limit: int = 100)-> GetFollowersResponse:
    cursor = cursor or datetime.now(UTC)
    if requesting_user_id == target_user_id:
        # Bypass privacy/blocked checks if the user is checking their own follower list
        query = """
        MATCH (user:User {user_id: $user_id})<-[:FOLLOWS]-(follower:User)
        WHERE follower.created_at < $cursor
        RETURN follower {
            .user_id,
            .profile_photo,
            .username,
            .display_name,
            .created_at
        } AS follower
        ORDER BY follower.created_at DESC
        LIMIT $limit
        """
    else:
        # Perform privacy and blocked checks for other users
        query = """
        MATCH (user:User {user_id: $user_id})
        MATCH (user)<-[:FOLLOWS]-(follower:User)
        OPTIONAL MATCH (user)-[:BLOCKS]-(follower)
        OPTIONAL MATCH (follower)-[:BLOCKS]-(user)
        WITH user, follower, COUNT(DISTINCT user) AS user_blocks, COUNT(DISTINCT follower) AS follower_blocks
        WHERE user.account_private = FALSE OR (user.account_private = TRUE AND (user)-[:FOLLOWS]->(follower))
        AND user_blocks = 0 AND follower_blocks = 0
        AND follower.created_at < $cursor
        RETURN follower {
            .user_id,
            .profile_photo,
            .username,
            .display_name,
            .created_at
        } AS follower
        ORDER BY follower.created_at DESC
        LIMIT $limit
        """

    async with driver.session() as session:
        fetch_result = await session.run(
            query,
            {
                "user_id": requesting_user_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        followers_data = await fetch_result.data()

        if not followers_data:
            return GetFollowersResponse(
                followers=[],
                has_more=False,
                last_follow_datetime=None,
            )

        followers_list = [
            SimpleUserResponse(
                user_id=user["follower"]["user_id"],
                profile_photo=user["follower"].get("profile_photo"),
                username=user["follower"].get("username"),
                display_name=user["follower"].get("display_name"),
                created_at=datetime.fromisoformat(user["follower"]["created_at"]),
            )
            for user in followers_data
        ]

        return GetFollowersResponse(
            followers=followers_list,
            has_more=len(followers_list) == limit,
            last_follow_datetime=(datetime.fromisoformat(followers_data[-1]["follower"]["created_at"]) if followers_list else None),
        )

async def get_follow_recommendations(requesting_user_id: str) -> GetFollowRecommendationsResponse:
    query = """
    MATCH (user:User {user_id: $user_id, account_active: true})
    MATCH (potential_follow:User {account_active: true})
    WHERE NOT (user)-[:FOLLOWS]->(potential_follow)
      AND user <> potential_follow
      AND NOT (user)-[:BLOCKS|MUTES]-(potential_follow)

    // Common Follows
    OPTIONAL MATCH (user)-[:FOLLOWS]->(common_follow:User)-[:FOLLOWS]->(potential_follow)
    WITH user, potential_follow, COUNT(DISTINCT common_follow) AS common_follows_count

    // Followers of followers
    OPTIONAL MATCH (user)<-[:FOLLOWS]-(follower:User)-[:FOLLOWS]->(potential_follow)
    WITH user, potential_follow, common_follows_count, COUNT(DISTINCT follower) AS follower_of_follower_count

    // Interactions (likes, reposts, quotes, replies, bookmarks)
    OPTIONAL MATCH (user)-[interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(post:Post)<-[:POSTED]-(potential_follow)
    OPTIONAL MATCH (user)-[:BOOKMARKED]->(:Bookmark)-[:BOOKMARKS]->(post:Post)<-[:POSTED]-(potential_follow)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count,
         COUNT(DISTINCT interaction) + COUNT(DISTINCT post) AS interaction_count

    // Dating interactions
    OPTIONAL MATCH (user)-[swipe_right:SWIPED_RIGHT]->(potential_follow)
    OPTIONAL MATCH (user)-[swipe_left:SWIPED_LEFT]->(potential_follow)
    OPTIONAL MATCH (potential_follow)-[swipe_right_on_user:SWIPED_RIGHT]->(user)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count,
         COUNT(swipe_right) AS swiped_right_count,
         COUNT(swipe_left) AS swiped_left_count,
         COUNT(swipe_right_on_user) AS swiped_right_on_user_count

    // Location similarity (profile and recent)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count,
         swiped_right_count, swiped_left_count, swiped_right_on_user_count,
         CASE
             WHEN user.profile_location IS NOT NULL AND potential_follow.profile_location IS NOT NULL
             THEN point.distance(
                 point({latitude: user.profile_location[0], longitude: user.profile_location[1]}),
                 point({latitude: potential_follow.profile_location[0], longitude: potential_follow.profile_location[1]})
             )
             ELSE NULL
         END AS profile_distance,
         CASE
             WHEN user.recent_location IS NOT NULL AND potential_follow.recent_location IS NOT NULL
             THEN point.distance(
                 point({latitude: user.recent_location[0], longitude: user.recent_location[1]}),
                 point({latitude: potential_follow.recent_location[0], longitude: potential_follow.recent_location[1]})
             )
             ELSE NULL
         END AS recent_distance

    // Age similarity
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count,
         profile_distance, recent_distance, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
         CASE
             WHEN user.birth_datetime_utc IS NOT NULL AND potential_follow.birth_datetime_utc IS NOT NULL
             THEN abs(duration.between(date(user.birth_datetime_utc), date(potential_follow.birth_datetime_utc)).years)
             ELSE NULL
         END AS age_difference

    // Common schools and organizations
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(potential_follow)
    OPTIONAL MATCH (user)-[:MEMBER_OF]->(organization:Organization)<-[:MEMBER_OF]-(potential_follow)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count,
         profile_distance, recent_distance, age_difference, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
         COUNT(DISTINCT school) AS common_school_count,
         COUNT(DISTINCT organization) AS common_organization_count

    // Calculate weighted score
    WITH user, potential_follow,
         common_follows_count * 4 +
         follower_of_follower_count * 3 +
         interaction_count * 5 +
         common_organization_count * 2 +
         CASE WHEN profile_distance IS NOT NULL THEN 2 * exp(-profile_distance / 1000) ELSE 0 END +
         CASE WHEN recent_distance IS NOT NULL THEN 2 * exp(-recent_distance / 1000) ELSE 0 END +
         CASE WHEN age_difference IS NOT NULL THEN 2 * exp(-age_difference / 10) ELSE 0 END +
         common_school_count * 3 +
         swiped_right_count * 5 +
         swiped_right_on_user_count * 5 -
         swiped_left_count * 10 AS score

    RETURN potential_follow {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .created_at
    } AS recommended_user,
    score
    ORDER BY score DESC
    LIMIT 20
    """

    async with driver.session() as session:
        result = await session.run(query, {"user_id": requesting_user_id})
        records = await result.data()
        recommendations = [
            SimpleUserResponse(
                user_id=record["recommended_user"]["user_id"],
                username=record["recommended_user"]["username"],
                display_name=record["recommended_user"]["display_name"],
                profile_photo=record["recommended_user"].get("profile_photo"),
                created_at=datetime.fromisoformat(record["recommended_user"]["created_at"]),
            )
            for record in records
        ]
    return GetFollowRecommendationsResponse(recommendations=recommendations)


"""---------------- BLOCKS -----------------"""
async def get_block_list(requesting_user_id: str) -> BlockedUsersResponse:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})-[r:BLOCKS]->(blocked_user:User)
    RETURN blocked_user.user_id AS user_id,
        blocked_user.profile_photo AS profile_photo,
        blocked_user.username AS username,
        blocked_user.display_name AS display_name,
        r.created_at AS created_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No blocked users found.",
            )
        return BlockedUsersResponse(
            blocked_list=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["blocked_list"]
            ],
        )

async def block_user(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})
    MATCH (blocked_user:User {user_id: $target_user_id})
    MERGE (user)-[r:BLOCKS {created_at: $created_at}]->(blocked_user)
    WITH user, blocked_user
    OPTIONAL MATCH (user)-[f1:FOLLOWS]->(blocked_user)
    OPTIONAL MATCH (blocked_user)-[f2:FOLLOWS]->(user)
    DELETE f1, f2
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return True

async def unblock_user(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MATCH (user:User {user_id: $requesting_user_id})-[r:BLOCKS]->(blocked_user:User {user_id: $target_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return True


"""---------------- SEARCH -----------------"""
async def visited_profile(requesting_user_id: str, target_user_id: str) -> bool:
    query = """
    MERGE (requesting_user:User {user_id: $requesting_user_id})-[r:VISITED_PROFILE]->(target_user:User {user_id: $target_user_id})
    ON CREATE
        SET target_user.last_visited_profile = $visited_at
        SET r.visit_count = COALESCE(r.visit_count, 0) + 1
    ON MATCH
        SET target_user.last_visited_profile = $visited_at
        SET r.visit_count = COALESCE(r.visit_count, 0) + 1
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "target_user_id": target_user_id,
                "visited_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return True
