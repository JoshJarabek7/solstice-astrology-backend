from datetime import datetime

from fastapi import Depends, Query
from faststream.kafka.fastapi import KafkaRouter

from app.posts.db import (
    bookmark_group_exists_for_user,
    create_bookmark_group,
    create_general_post,
    delete_bookmark_group,
    delete_post,
    get_bookmark_groups,
    get_general_feed,
    get_likes_for_post,
    get_post,
    get_post_replies,
    get_quoters,
    get_reposters,
    update_bookmark_group,
)
from app.posts.schemas import (
    BookmarkGroupsResponse,
    CreateBookmarkGroupRequest,
    CreatePostRequest,
    GetBookmarkGroupRequest,
    PostFeedRequest,
    PostLikesResponse,
    PostRepliesResponse,
    PostResponse,
    PostsResponse,
    QuotersResponse,
    RepostersResponse,
    UpdateBookmarkGroupRequest,
)
from app.shared.auth import get_current_user
from app.users.schemas import VerifiedUser

router = KafkaRouter()

@router.post("/api/post/feed/general", response_model=PostsResponse)
async def get_general_feed_route(
    request: PostFeedRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostsResponse:
    return await get_general_feed(verified_user.user_id, exclude_post_ids=request.exclude_post_ids, limit=request.limit)

@router.post("/api/post/general", response_model=PostResponse)
async def create_general_post_route(request: CreatePostRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> PostResponse:
    return await create_general_post(verified_user.user_id, request)

@router.get("/api/post/{post_id}", response_model=PostResponse)
async def get_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostResponse:
    return await get_post(post_id, verified_user.user_id)


@router.delete("/api/post/{post_id}", response_model=None)
async def delete_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    return await delete_post(post_id, verified_user.user_id)


@router.get("/api/post/like/{post_id}", response_model=PostLikesResponse)
async def get_post_likes_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostLikesResponse:
    return await get_likes_for_post(post_id, verified_user.user_id, cursor, limit)


@router.get("/api/post/repost/{post_id}", response_model=RepostersResponse)
async def get_reposts_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> RepostersResponse:
    return await get_reposters(post_id, verified_user.user_id, cursor, limit)


@router.get("/api/post/quote/{post_id}", response_model=QuotersResponse)
async def get_quoters_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> QuotersResponse:
    return await get_quoters(post_id, verified_user.user_id, cursor, limit)

@router.get("/api/post/reply/{post_id}", response_model=PostRepliesResponse)
async def get_post_replies_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostRepliesResponse:
    return await get_post_replies(post_id, verified_user.user_id, cursor, limit)

@router.post("/api/bookmark/group/list", response_model=BookmarkGroupsResponse)
async def get_bookmark_groups_route(
    request: GetBookmarkGroupRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BookmarkGroupsResponse:
    return await get_bookmark_groups(verified_user.user_id, request.excluded_post_ids, request.limit)

@router.get("/api/bookmark/group/exists/{group_name}", response_model=bool)
async def check_bookmark_group_exists_for_user_route(
    group_name: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> bool:
    return await bookmark_group_exists_for_user(verified_user.user_id, group_name)


@router.post("/api/bookmark/group", response_model=None)
async def create_bookmark_group_route(
    request: CreateBookmarkGroupRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    return await create_bookmark_group(verified_user.user_id, request)

@router.put("/api/bookmark/group/{bookmark_group_id}", response_model=bool)
async def update_bookmark_group_route(
    bookmark_group_id: str,
    request: UpdateBookmarkGroupRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> bool:
    return await update_bookmark_group(verified_user.user_id, bookmark_group_id, request)

@router.delete("/api/bookmark/group/{bookmark_group_id}", response_model=bool)
async def delete_bookmark_group_route(
    bookmark_group_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> bool:
    return await delete_bookmark_group(verified_user.user_id, bookmark_group_id)
