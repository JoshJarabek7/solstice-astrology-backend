from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.class_validators import root_validator

from app.users.schemas import SimpleUserResponse


class PostResponse(BaseModel):
    """Response model for getting a post."""

    post_id: str
    content: str
    created_at: datetime
    post_type: str
    is_video: bool
    video_url: str | None = None
    video_length: float | None = None
    like_count: int = 0
    view_count: int = 0
    attachments: list[str] | None = None
    quote_count: int = 0
    reply_count: int = 0
    repost_count: int = 0
    bookmark_count: int = 0
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    poster: SimpleUserResponse
    quoted_post: Optional["PostResponse"] | None = None
    replied_post: Optional["PostResponse"] | None = None
    quoted_post_private: bool = False
    replied_post_private: bool = False

    class Config:
        """Configures the model."""

        arbitrary_types_allowed = True

class PostsResponse(BaseModel):
    posts: list[PostResponse]
    has_more: bool
    next_cursor: datetime | None = None

class CreatePostRequest(BaseModel):
    """Request model for creating a new post."""

    content: str
    post_type: str = "general"
    is_video: bool = False
    video_url: str | None = None
    video_length: float | None = None
    attachments: list[str] | None = None
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    quoted_post_id: str | None = None
    replied_post_id: str | None = None
    reposted_post_id: str | None = None
    created_at: datetime = datetime.now(UTC)

class PostLikesResponse(BaseModel):
    """Response model for getting a list of likes for a post."""

    likes: list[SimpleUserResponse]
    has_more: bool
    last_like_datetime: datetime | None = None

class RepostersResponse(BaseModel):
    reposts: list[SimpleUserResponse]
    has_more: bool
    last_repost_datetime: datetime | None = None

class QuoterResponse(BaseModel):
    quoter: SimpleUserResponse
    post: PostResponse
    created_at: datetime


class QuotersResponse(BaseModel):
    quotes: list[QuoterResponse]
    has_more: bool
    next_cursor: datetime | None = None

class PostReplyResponse(BaseModel):
    replier: SimpleUserResponse
    post: PostResponse
    created_at: datetime

class PostRepliesResponse(BaseModel):
    replies: list[PostReplyResponse]
    has_more: bool
    next_cursor: datetime | None = None


class PostFeedRequest(BaseModel):
    exclude_post_ids: list[str] = []
    limit: int = 20

"""--------------- BOOKMARKS -----------------"""

class BookmarkRequest(BaseModel):
    bookmark_group_id: str
    post_id: str

class CreateBookmarkGroupRequest(BaseModel):
    name: str
    photo_url: str | None = None
    description: str | None = None
    public: bool = False
    bookmark_count: int = 0

class BookmarkGroupResponse(CreateBookmarkGroupRequest):
    bookmark_group_id: str
    updated_at: datetime
    created_at: datetime

class BookmarkGroupsResponse(BaseModel):
    bookmark_groups: list[BookmarkGroupResponse]
    has_more: bool
    next_cursor: datetime | None = None

class BookmarkResponse(BaseModel):
    bookmark_id: str
    post: PostResponse
    created_at: datetime

class BookmarksResponse(BaseModel):
    bookmarks: list[BookmarkResponse]
    has_more: bool
    next_cursor: datetime | None = None

class UpdateBookmarkGroupRequest(BaseModel):
    name: str | None = None
    photo_url: str | None = None
    description: str | None = None
    public: bool | None = None

class GetBookmarkGroupRequest(BaseModel):
    bookmark_group_id: str
    excluded_post_ids: list[str] = []
    limit: int = 10

"""---------------- SEARCH -----------------"""

class SearchPostsRequest(BaseModel):
    general_string: str | None = None
    must_contain: list[str] | None = None
    exclude: list[str] | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    profiles: list[str] | None = None
    following_only: bool | None = False

    @root_validator
    def check_must_or_contain(cls):
        if not cls.must_contain and not cls.general_string:
            raise ValueError("Must contain or can contain must be provided.")
        return cls
