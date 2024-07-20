from datetime import UTC, datetime
from typing import LiteralString, cast
from uuid import uuid4

from fastapi import HTTPException, status
from loguru import logger

from app.posts.schemas import (BookmarkGroupResponse, BookmarkGroupsResponse,
                               BookmarkResponse, BookmarksResponse,
                               CreateBookmarkGroupRequest, CreatePostRequest,
                               PostLikesResponse, PostRepliesResponse,
                               PostReplyResponse, PostResponse, PostsResponse,
                               QuoterResponse, QuotersResponse,
                               RepostersResponse, UpdateBookmarkGroupRequest)
from app.shared.neo4j import driver
from app.users.schemas import SimpleUserResponse


async def get_general_feed(user_id: str, exclude_post_ids: list[str], limit: int = 10) -> PostsResponse:
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (potential_post:Post)
    WHERE NOT potential_post.post_id IN $exclude_post_ids

    // Avoid posts that the user has already seen
    OPTIONAL MATCH (user)-[:VIEWED]->(potential_post)
    WITH user, potential_post, COUNT(DISTINCT potential_post) AS seen_count

    // Common interactions by people followed by the user
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[interaction:LIKED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[:REPOSTED]->(potential_post)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WITH user, potential_post, seen_count, COUNT(DISTINCT interaction) + COUNT(DISTINCT follower) + COUNT(DISTINCT bookmark) AS interaction_count

    // Posts by followed users
    OPTIONAL MATCH (user)-[:FOLLOWS]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, COUNT(DISTINCT poster) AS poster_count

    // Posts liked or reposted by similar users
    OPTIONAL MATCH (similar_user:User)-[similar_interaction:LIKED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (similar_user)-[:REPOSTED]->(potential_post)
    OPTIONAL MATCH (similar_user)-[:BOOKMARKED]->(similar_bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WHERE (user)-[:LIKED|QUOTED|REPLIED]->(:Post)<-[:LIKED|QUOTED|REPLIED]-(similar_user)
    OR (user)-[:REPOSTED]->(:Post)<-[:REPOSTED]-(similar_user)
    OR (user)-[:BOOKMARKED]->(:Bookmark)-[:BOOKMARKS]->(:Post)<-[:BOOKMARKED]-(similar_user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, COUNT(DISTINCT similar_interaction) + COUNT(DISTINCT similar_user) + COUNT(DISTINCT similar_bookmark) AS similar_interaction_count

    // Distance similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count,
        CASE
            WHEN user.profile_location IS NOT NULL AND potential_post.location IS NOT NULL
            THEN point.distance(point({latitude: user.profile_location[0], longitude: user.profile_location[1]}),
                                point({latitude: potential_post.location[0], longitude: potential_post.location[1]}))
            ELSE null
        END AS distance

    // Age similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance,
        CASE
            WHEN user.birth_datetime_utc IS NOT NULL AND potential_post.birth_datetime_utc IS NOT NULL
            THEN abs(duration.between(date(user.birth_datetime_utc), date(potential_post.birth_datetime_utc)).years)
            ELSE null
        END AS age_difference

    // Common schools
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference,
        COUNT(DISTINCT school) AS common_schools_count

    // Check for blocks and mutes
    OPTIONAL MATCH (potential_post)-[:QUOTED|REPLIED]->(original_post:Post)
    OPTIONAL MATCH (original_poster:User)-[:POSTED]->(original_post)
    OPTIONAL MATCH (user)-[:BLOCKS|MUTES]->(original_poster)
    OPTIONAL MATCH (original_poster)-[:BLOCKS|MUTES]->(user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count,
        COUNT(DISTINCT original_poster) AS block_mute_count
    // Check for swipe right
    OPTIONAL MATCH (user)-[:SWIPED_RIGHT]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count, block_mute_count,
        COUNT(DISTINCT poster) AS swipe_right_count

    // Calculate weighted score
    WITH potential_post,
        (CASE WHEN seen_count > 0 THEN -100 ELSE 0 END) +
        (CASE WHEN block_mute_count > 0 THEN -100 ELSE 0 END) +
        swipe_right_count * 10 +
        interaction_count * 5 +
        poster_count * 3 +
        similar_interaction_count * 4 +
        (CASE WHEN distance IS NOT NULL THEN 2 * EXP(-distance / 1000) ELSE 0 END) +
        (CASE WHEN age_difference IS NOT NULL THEN 2 * EXP(-age_difference / 10) ELSE 0 END) +
        common_schools_count * 2 AS score
    WHERE score > 0
    MATCH (poster:User)-[:POSTED]->(potential_post)
    RETURN potential_post.post_id AS post_id, potential_post.content AS content,
        potential_post.created_at AS created_at,
        potential_post.post_type AS post_type,
        potential_post.is_video AS is_video,
        potential_post.video_url AS video_url,
        potential_post.video_length AS video_length,
        potential_post.like_count AS like_count,
        potential_post.view_count AS view_count,
        potential_post.quote_count AS quote_count,
        potential_post.reply_count AS reply_count,
        potential_post.repost_count AS repost_count,
        potential_post.bookmark_count AS bookmark_count,
        potential_post.mentions AS mentions,
        potential_post.hashtags AS hashtags,
        potential_post.quoted_post AS quoted_post,
        potential_post.replied_post AS replied_post,
        potential_post.quoted_post_private AS quoted_post_private,
        potential_post.replied_post_private AS replied_post_private,
        poster {
            .user_id,
            .username,
            .display_name,
            .profile_photo
        },
        score
    ORDER BY score DESC, potential_post.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "exclude_post_ids": exclude_post_ids,
                "limit": limit,
            }
        )
        response_data = await result.data()
        if not response_data:
            raise HTTPException(
                status_code=404,
                detail="No posts found or access denied",
            )
        posts = [
            PostResponse(
                post_id=record["post_id"] or "",
                content=record["content"] or "",
                created_at=record["created_at"] or datetime.now(UTC),
                post_type=record["post_type"] or "",
                is_video=record["is_video"] or False,
                video_url=record["video_url"],
                video_length=record["video_length"],
                like_count=record["like_count"] or 0,
                view_count=record["view_count"] or 0,
                attachments=record["attachments"],
                quote_count=record["quote_count"] or 0,
                reply_count=record["reply_count"] or 0,
                repost_count=record["repost_count"] or 0,
                bookmark_count=record["bookmark_count"] or 0,
                poster=SimpleUserResponse(**record["poster"]),
                mentions=record["mentions"],
                hashtags=record["hashtags"],
                quoted_post=record["quoted_post"],
                replied_post=record["replied_post"],
                quoted_post_private=record["quoted_post_private"] or False,
                replied_post_private=record["replied_post_private"] or False,
            )
            for record in response_data[:limit]
        ]
        has_more = len(response_data) > limit
        if has_more:
            next_cursor = datetime.fromisoformat(response_data[-1]["created_at"])
        else:
            next_cursor = None
        return PostsResponse(
            posts=posts,
            has_more=has_more,
            next_cursor=next_cursor,
        )

async def create_general_post(user_id: str, request: CreatePostRequest) -> PostResponse:
    """Create a general post for a user."""
    post_id = str(uuid4())
    post_data = request.model_dump()
    post_data["post_id"] = post_id
    query = """
    CREATE (new_post:Post {
        post_id: $post_id,
        content: $content,
        created_at: $created_at,
        post_type: $post_type,
        is_video: $is_video,
        video_url: $video_url,
        video_length: $video_length,
        like_count: 0,
        view_count: 0,
        quote_count: 0,
        reply_count: 0,
        repost_count: 0,
        bookmark_count: 0,
        mentions: $mentions,
        hashtags: $hashtags
    })
    RETURN new_post
    """
    async with driver.session() as session:
        await session.run(
            query,
            {
                "post_id": post_id,
                "content": post_data["content"],
                "created_at": post_data["created_at"].isoformat(),
                "post_type": post_data["post_type"],
                "is_video": post_data["is_video"],
                "video_url": post_data["video_url"],
                "video_length": post_data["video_length"],
                "mentions": post_data["mentions"],
                "hashtags": post_data["hashtags"],
            }
        )
        if request.quoted_post_id:
            query = """
                MATCH (p:Post {post_id: $post_id}), (quoted:Post {post_id: $quoted_post_id})
                CREATE (p)-[:QUOTED {created_at: $created_at}]->(quoted)
            """
            await session.run(
                query,
                {
                    "post_id": post_id,
                    "quoted_post_id": request.quoted_post_id,
                    "created_at": request.created_at.isoformat(),
                },
            )
        if request.replied_post_id:
            query = """
                MATCH (p:Post {post_id: $post_id}), (replied:Post {post_id: $replied_post_id})
                CREATE (p)-[:REPLIED {created_at: $created_at}]->(replied)
            """
            await session.run(
                query,
                {
                    "post_id": post_id,
                    "replied_post_id": request.replied_post_id,
                    "created_at": request.created_at.isoformat(),
                },
            )
        if request.reposted_post_id:
            query = """
                MATCH (p:Post {post_id: $post_id}), (reposted:Post {post_id: $reposted_post_id})
                CREATE (p)-[:REPOSTED {created_at: $created_at}]->(reposted)
            """
            await session.run(
                query,
                {
                    "post_id": post_id,
                    "reposted_post_id": request.reposted_post_id,
                    "created_at": request.created_at.isoformat(),
                },
            )
        result =await session.run(
            """
            MATCH (p:Post {post_id: $post_id})
            MATCH (user:User {user_id: $user_id})
            CREATE (p)-[:POSTED {created_at: $created_at}]->(user)
            RETURN p.post_id AS post_id
            """,
            {
                "post_id": post_id,
                "user_id": user_id,
                "created_at": request.created_at.isoformat(),
            },
        )
        post_data = await result.single()
        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )
        post_id = post_data["post_id"]
        logger.info(f"Successfully created post {post_id}")
        return PostResponse(**post_data)


async def get_post(post_id: str, user_id: str) -> PostResponse:
    query = """
    MATCH (post:Post {post_id: $post_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    OPTIONAL MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (requester)-[:BLOCKS]-(author)
    WITH post, author, requester, COUNT(DISTINCT author) AS block_count, COUNT(DISTINCT requester) AS follows_count
    WHERE block_count = 0 AND (NOT author.account_private OR follows_count > 0)

    OPTIONAL MATCH (post)-[:QUOTED]->(quoted_post:Post)
    OPTIONAL MATCH (post)-[:REPLIED]->(replied_post:Post)

    OPTIONAL MATCH (quoted_post)<-[:POSTED]-(quoted_author:User)
    OPTIONAL MATCH (replied_post)<-[:POSTED]-(replied_author:User)

    RETURN post {
        .post_id,
        .content,
        .created_at,
        .post_type,
        .is_video,
        .video_url,
        .video_length,
        .like_count,
        .view_count,
        .quote_count,
        .reply_count,
        .repost_count,
        .bookmark_count,
        .mentions,
        .hashtags,
        poster: author {
            .user_id,
            .username,
            .display_name,
            .profile_photo
        },
        quoted_post: CASE WHEN quoted_post IS NOT NULL AND (NOT quoted_author.account_private OR (requester)-[:FOLLOWS]->(quoted_author))
            THEN quoted_post {
                .post_id,
                .content,
                .created_at,
                .post_type,
                .is_video,
                .video_url,
                .video_length,
                .like_count,
                .view_count,
                .quote_count,
                .reply_count,
                .repost_count,
                .bookmark_count,
                .mentions,
                .hashtags,
                poster: quoted_author {
                    .user_id,
                    .username,
                    .display_name,
                    .profile_photo
                }
            }
            ELSE NULL END,
        replied_post: CASE WHEN replied_post IS NOT NULL AND (NOT replied_author.account_private OR (requester)-[:FOLLOWS]->(replied_author))
            THEN replied_post {
                .post_id,
                .content,
                .created_at,
                .post_type,
                .is_video,
                .video_url,
                .video_length,
                .like_count,
                .view_count,
                .quote_count,
                .reply_count,
                .repost_count,
                .bookmark_count,
                .mentions,
                .hashtags,
                poster: replied_author {
                    .user_id,
                    .username,
                    .display_name,
                    .profile_photo
                }
            }
            ELSE NULL END,
        quoted_post_private: CASE WHEN quoted_post IS NOT NULL AND quoted_author.account_private AND NOT (requester)-[:FOLLOWS]->(quoted_author)
            THEN true
            ELSE false END,
        replied_post_private: CASE WHEN replied_post IS NOT NULL AND replied_author.account_private AND NOT (requester)-[:FOLLOWS]->(replied_author)
            THEN true
            ELSE false END
    } AS post_data
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )
        post_data = record["post_data"]
        return PostResponse(**post_data)


async def delete_post(post_id: str, user_id: str) -> None:
    query = """
    MATCH (post:Post {post_id: $post_id})<-[:POSTED]-(author:User {user_id: $user_id})

    // Decrement quote_count on quoted posts
    OPTIONAL MATCH (post)-[q:QUOTED]->(quoted_post:Post)
    WITH post, author, collect({post: quoted_post, rel: q}) as quoted_posts

    // Decrement reply_count on replied posts
    OPTIONAL MATCH (post)-[r:REPLIED]->(replied_post:Post)
    WITH post, author, quoted_posts, collect({post: replied_post, rel: r}) as replied_posts

    // Delete relationships and update counts
    UNWIND quoted_posts AS qp
    SET qp.post.quote_count = CASE WHEN qp.post.quote_count > 0 THEN qp.post.quote_count - 1 ELSE 0 END
    DELETE qp.rel

    WITH post, author, replied_posts
    UNWIND replied_posts AS rp
    SET rp.post.reply_count = CASE WHEN rp.post.reply_count > 0 THEN rp.post.reply_count - 1 ELSE 0 END
    DELETE rp.rel

    // Delete other relationships
    WITH post, author
    OPTIONAL MATCH (post)-[other_rel]-()
    DELETE other_rel

    WITH post, author
    OPTIONAL MATCH ()-[incoming_rel]->(post)
    DELETE incoming_rel

    // Delete the post
    WITH post, author
    DETACH DELETE post

    RETURN COUNT(post) AS deleted_count
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "user_id": user_id,
            },
        )
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to delete it.",
            )
        return None

async def get_likes_for_post(post_id: str, user_id: str, cursor: datetime | None = None, limit: int = 10) -> PostLikesResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (liker:User)-[like:LIKED]->(post)
    WHERE like.created_at < $cursor
        AND NOT (liker)-[:BLOCKS]-(requester)
    RETURN liker {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        created_at: like.created_at
    } AS like_data
    ORDER BY like.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.data()

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )

        likes = [SimpleUserResponse(**record["like_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["like_data"]["created_at"] if has_more else None

        return PostLikesResponse(
            likes=likes,
            has_more=has_more,
            last_like_datetime=next_cursor,
        )

async def get_reposters(post_id: str, user_id: str, cursor: datetime | None = None, limit: int = 10) -> RepostersResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (reposter:User)-[repost:REPOSTED]->(post)
    WHERE repost.created_at < $cursor
        AND NOT (reposter)-[:BLOCKS]-(requester)
    RETURN reposter {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        created_at: repost.created_at
    }
    ORDER BY repost.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.data()

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )

        reposts = [SimpleUserResponse(**record["repost_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["repost_data"]["created_at"] if has_more else None

        return RepostersResponse(
            reposts=reposts,
            has_more=has_more,
            last_repost_datetime=next_cursor,
        )

async def repost(post_id: str, user_id: str) -> None:
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post is NOT NULL AND NOT author.account_private
    // We don't want to repost private posts
    // We also don't want to repost posts that the user has already reposted
    AND NOT (requester)-[:REPOSTED]->(post)

    MERGE (requester)-[r:REPOSTED {created_at: $created_at}]->(post)
    ON CREATE SET post.repost_count = COALESCE(post.repost_count, 0) + 1
    RETURN r AS repost, author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to repost post.")
        return None

async def unrepost(post_id: str, user_id: str) -> None:
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    MATCH (requester)-[r:REPOSTED]->(post)
    DELETE r
    SET post.repost_count = CASE WHEN post.repost_count > 0 THEN post.repost_count - 1 ELSE 0 END
    RETURN author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
            }
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Post not found or you haven't reposted this post.")
        return None

async def get_quoters(post_id: str, user_id: str, cursor: datetime | None = None, limit: int = 10) -> QuotersResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (original_post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    WHERE NOT (original_post)<-[:POSTED]-(:User)-[:BLOCKS]-(requester)
      AND (NOT exists((original_post)<-[:POSTED]-(:User {account_private: true}))
           OR (original_post)<-[:POSTED]-(:User)<-[:FOLLOWS]-(requester))

    MATCH (quoter:User)-[:POSTED]->(quote:Post)-[r:QUOTED]->(original_post)
    WHERE r.created_at < $cursor
        AND NOT (quoter)-[:BLOCKS]-(requester) AND (NOT quoter.account_private OR (requester)-[:FOLLOWS]->(quoter))
    WITH quoter, quote, r.created_at AS quote_created_at
    ORDER BY quote_created_at DESC
    LIMIT $limit + 1

    RETURN {
        quoter: quoter {
            .user_id,
            .username,
            .display_name,
            .profile_photo
        },
        post: quote {
            .post_id,
            .content,
            .created_at,
            .post_type,
            .is_video,
            .video_url,
            .video_length,
            .like_count,
            .view_count,
            .quote_count,
            .reply_count,
            .repost_count,
            .bookmark_count,
            .mentions,
            .hashtags
        },
        created_at: quote_created_at
    } AS quote_data
    ORDER BY quote_data.created_at DESC
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        records = await result.data()

        if not records:
            return QuotersResponse(quotes=[], has_more=False, next_cursor=None)

        quotes = [
            QuoterResponse(
                quoter=SimpleUserResponse(**record["quote_data"]["quoter"]),
                post=PostResponse(**record["quote_data"]["post"]),
                created_at=datetime.fromisoformat(record["quote_data"]["created_at"])
            )
            for record in records
        ]

        has_more = len(records) > limit
        next_cursor = records[-1]["quote_data"]["created_at"] if has_more else None

        return QuotersResponse(
            quotes=quotes,
            has_more=has_more,
            next_cursor=next_cursor,
        )

async def get_post_replies(post_id: str, user_id: str, cursor: datetime | None = None, limit: int = 10) -> PostRepliesResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (replier:User)-[:POSTED]->(reply:Post)-[r:REPLIED]->(post)
    WHERE r.created_at < $cursor
        AND NOT (replier)-[:BLOCKS]-(requester)
        AND (NOT replier.account_private OR (requester)-[:FOLLOWS]->(replier))
    WITH reply, replier, r.created_at AS reply_created_at
    ORDER BY reply_created_at DESC
    LIMIT $limit + 1

    RETURN {
        reply: reply {.*},
        replier: replier {
            .user_id,
            .username,
            .display_name,
            .profile_photo
        },
        created_at: reply_created_at
    } AS reply_data
    ORDER BY reply_data.created_at DESC
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": user_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        records = await result.data()

        if not records:
            return PostRepliesResponse(replies=[], has_more=False, next_cursor=None)

        replies = [
            PostReplyResponse(
                post=PostResponse(**record["reply_data"]["reply"]),
                replier=SimpleUserResponse(**record["reply_data"]["replier"]),
                created_at=datetime.fromisoformat(record["reply_data"]["created_at"])
            )
            for record in records
        ]

        has_more = len(records) > limit
        next_cursor = records[-1]["reply_data"]["created_at"] if has_more else None

        return PostRepliesResponse(
            replies=replies,
            has_more=has_more,
            next_cursor=next_cursor,
        )

"""--------------- BOOKMARKS -----------------"""

async def get_bookmark_groups(user_id: str, exclude_group_ids: list[str] = [], limit: int = 10) -> BookmarkGroupsResponse:
    query = """
    MATCH (u:User {user_id: $user_id})-[:OWNS]->(bg:BookmarkGroup)
    WHERE NOT bg.bookmark_group_id IN $exclude_group_ids
    WITH u, bg
    ORDER BY bg.updated_at DESC
    LIMIT $limit + 1
    RETURN {
        bookmark_group: bg {.*},
        created_at: bg.created_at,
        updated_at: bg.updated_at
    } AS bookmark_group_data
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "exclude_group_ids": exclude_group_ids,
                "limit": limit,
            },
        )
        records = await result.data()

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark groups not found.",
            )
        bookmark_groups = [BookmarkGroupResponse(**record["bookmark_group_data"]) for record in records]

        has_more = len(records) > limit
        next_cursor = records[-1]["bookmark_group_data"]["updated_at"] if has_more else None

        return BookmarkGroupsResponse(
            bookmark_groups=bookmark_groups,
            has_more=has_more,
            next_cursor=next_cursor,
        )

async def bookmark_group_exists_for_user(user_id: str, group_name: str) -> bool:
    query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {name: $group_name})
    RETURN COUNT(group) > 0 AS exists
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "group_name": group_name,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark group not found.",
            )
        return record["exists"]

async def create_bookmark_group(user_id: str, request: CreateBookmarkGroupRequest) -> None:
    query = """
    MATCH (user:User {user_id: $user_id})
    CREATE (user)-[:OWNS]->(bookmark_group:BookmarkGroup {
        bookmark_group_id: $bookmark_group_id,
        name: $name,
        photo_url: $photo_url,
        description: $description,
        public: $public,
        bookmark_count: 0,
        updated_at: $updated_at,
        created_at: $created_at
    })
    RETURN bookmark_group
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "name": request.name,
                "photo_url": request.photo_url,
                "description": request.description,
                "public": request.public,
                "updated_at": datetime.now(UTC).isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark group not found.",
            )


async def get_bookmark_group(user_id: str, bookmark_group_id: str, cursor: datetime | None = None, limit: int = 10) -> BookmarksResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    MATCH (group)-[:CONTAINS]->(bookmark:Bookmark)-[:BOOKMARKS]->(post:Post)
    WHERE bookmark.created_at < $cursor

    // Check if the original poster has blocked the user or vice versa
    MATCH (post)<-[:POSTED]-(original_poster:User)
    WHERE NOT (original_poster)-[:BLOCKS]-(user)
    AND (NOT original_poster.account_private OR (user)-[:FOLLOWS]->(original_poster))

    // Fetch quote post if exists
    OPTIONAL MATCH (post)-[:QUOTED]->(quoted_post:Post)<-[:POSTED]-(quoted_poster:User)
    WHERE NOT (quoted_poster)-[:BLOCKS]-(user)
    AND (NOT quoted_poster.account_private OR (user)-[:FOLLOWS]->(quoted_poster))

    WITH user, group, bookmark, post, original_poster, quoted_post, quoted_poster
    ORDER BY bookmark.created_at DESC
    LIMIT $limit

    // Group the results before final aggregation
    WITH group, collect({
    bookmark: bookmark,
    post: post,
    original_poster: original_poster,
    quoted_post: quoted_post,
    quoted_poster: quoted_poster
    }) AS bookmark_data

    RETURN {
    bookmark_group: group {.*},
    bookmarks: [b IN bookmark_data | {
        bookmark: {
        bookmark_id: b.bookmark.bookmark_id,
        created_at: b.bookmark.created_at
        // Add any other bookmark properties you need
        },
        post: {
        post_id: b.post.post_id,
        content: b.post.content,
        created_at: b.post.created_at,
        post_type: b.post.post_type,
        is_video: b.post.is_video,
        video_url: b.post.video_url,
        video_length: b.post.video_length,
        like_count: b.post.like_count,
        view_count: b.post.view_count,
        quote_count: b.post.quote_count,
        reply_count: b.post.reply_count,
        repost_count: b.post.repost_count,
        bookmark_count: b.post.bookmark_count,
        mentions: b.post.mentions,
        hashtags: b.post.hashtags,
        poster: {
            user_id: b.original_poster.user_id,
            username: b.original_poster.username,
            display_name: b.original_poster.display_name,
            profile_photo: b.original_poster.profile_photo
        },
        quoted_post: CASE
            WHEN b.quoted_post IS NOT NULL
            THEN {
            post_id: b.quoted_post.post_id,
            content: b.quoted_post.content,
            created_at: b.quoted_post.created_at,
            post_type: b.quoted_post.post_type,
            is_video: b.quoted_post.is_video,
            video_url: b.quoted_post.video_url,
            video_length: b.quoted_post.video_length,
            like_count: b.quoted_post.like_count,
            view_count: b.quoted_post.view_count,
            quote_count: b.quoted_post.quote_count,
            reply_count: b.quoted_post.reply_count,
            repost_count: b.quoted_post.repost_count,
            bookmark_count: b.quoted_post.bookmark_count,
            mentions: b.quoted_post.mentions,
            hashtags: b.quoted_post.hashtags,
            poster: {
                user_id: b.quoted_poster.user_id,
                username: b.quoted_poster.username,
                display_name: b.quoted_poster.display_name,
                profile_photo: b.quoted_poster.profile_photo
            }
            }
            ELSE null
        END
        }
    }]
    } AS result
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "bookmark_group_id": bookmark_group_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        record = await result.single()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark group not found or you don't have permission to view it.",
            )

        result_data = record["result"]
        # bookmark_group_data = result_data["bookmark_group"]
        bookmarks_data = result_data["bookmarks"]

        bookmarks: list[BookmarkResponse] = []
        for bookmark_data in bookmarks_data:
            post_data = bookmark_data["post"]
            quoted_post_data = post_data.pop("quoted_post", None)
            poster_data = post_data.pop("poster")

            if quoted_post_data:
                quoted_poster_data = quoted_post_data.pop("poster")
                quoted_post = PostResponse(
                    **quoted_post_data,
                    poster=SimpleUserResponse(**quoted_poster_data),
                    quoted_post=None,  # Assuming we don't need to go deeper than one level of quoting
                    replied_post=None,
                )
            else:
                quoted_post = None

            post = PostResponse(
                **post_data,
                poster=SimpleUserResponse(**poster_data),
                quoted_post=quoted_post,
                replied_post=None,  # We're not fetching replied_post in this query
            )

            bookmarks.append(BookmarkResponse(
                bookmark_id=bookmark_data["bookmark"]["bookmark_id"],
                post=post,
                created_at=datetime.fromisoformat(bookmark_data["bookmark"]["created_at"])
            ))

        next_cursor = bookmarks[-1].created_at if bookmarks else None

        return BookmarksResponse(
            bookmarks=bookmarks,
            has_more=len(bookmarks) == limit,
            next_cursor=next_cursor
        )

async def update_bookmark_group(user_id: str, bookmark_group_id: str, request: UpdateBookmarkGroupRequest) -> bool:
    base_query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    SET group.updated_at = $updated_at
    """

    params: dict[str, str | bool] = {
        "user_id": user_id,
        "bookmark_group_id": bookmark_group_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    if request.name is not None:
        base_query += ", group.name = $name"
        params["name"] = request.name

    if request.photo_url is not None:
        base_query += ", group.photo_url = $photo_url"
        params["photo_url"] = request.photo_url

    if request.description is not None:
        base_query += ", group.description = $description"
        params["description"] = request.description

    if request.public is not None:
        base_query += ", group.public = $public"
        params["public"] = request.public

    base_query += " RETURN group"

    literal_query = cast(LiteralString, base_query)
    async with driver.session() as session:
        result = await session.run(literal_query, params)
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark group not found.",
            )
        return True


async def delete_bookmark_group(user_id: str, bookmark_group_id: str) -> bool:
    query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    OPTIONAL MATCH (group)-[r:CONTAINS]->(bookmark:Bookmark)
    DETACH DELETE group, bookmark
    RETURN COUNT(group) AS deleted_count
    """

    params: dict[str, str] = {
        "user_id": user_id,
        "bookmark_group_id": bookmark_group_id,
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record or not record["deleted_count"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark group not found or you don't have permission to delete it.",
            )
        return True