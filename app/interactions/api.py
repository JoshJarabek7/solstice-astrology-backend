import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from faststream.kafka.fastapi import KafkaRouter
from loguru import logger

from app.interactions.schemas import (AddBookmarkEvent, AddBookmarkRequest,
                                      DeleteBookmarkEvent, LikedPostEvent,
                                      MatchEvent, SwipeRightEvent,
                                      UnlikedPostEvent, ViewedPostEvent,
                                      ViewedPostRequest, ViewedProfileEvent,
                                      ViewedProfileRequest)
from app.notifications.ws import WebSocketManager
from app.shared.auth import get_current_user
from app.shared.neo4j import driver
from app.users.schemas import VerifiedUser

router = KafkaRouter()


@router.subscriber("viewed.profile")
async def viewed_profile_event(event: ViewedProfileEvent) -> None:
    """Handles a viewed profile event."""
    logger.debug(f"Received viewed profile event: {event}")

    query = """
    MATCH (viewing_user:User {user_id: $viewing_user_id})
    MATCH (viewed_user:User {user_id: $viewed_user_id})

    // Create the view event
    CREATE (view:ProfileView {
        view_id: $view_id,
        created_at: $created_at
    })
    CREATE (viewing_user)-[:PERFORMED]->(view)-[:VIEWED]->(viewed_user)

    // Update or create the aggregation relationship
    MERGE (viewing_user)-[r:VIEWED_PROFILE]->(viewed_user)
    ON CREATE SET r.count = 1, r.first_viewed_at = $created_at
    ON MATCH SET r.count = r.count + 1
    SET r.last_viewed_at = $created_at, viewed_user.profile_visits_count = COALESCE(viewed_user.profile_visits_count, 0) + 1

    // Get recent view count for analysis
    WITH viewing_user, viewed_user, view
    MATCH (viewing_user)-[:PERFORMED]->(recent_view:ProfileView)-[:VIEWED]->(viewed_user)
    WHERE recent_view.created_at > datetime() - duration('P30D') // Views in last 30 days

    RETURN view.id AS view_id, r.count AS total_views, COUNT(recent_view) AS recent_views
    """
    params = {
        "viewing_user_id": event.viewing_user_id,
        "viewed_user_id": event.viewed_user_id,
        "created_at": datetime.now(UTC).isoformat(),
        "view_id": str(uuid4()),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if record:
            logger.info(f"Profile view recorded. View ID: {record['view_id']}, "
                        f"Total views: {record['total_views']}, "
                        f"Views in last 30 days: {record['recent_views']}"
            )
        else:
            logger.error("Failed to record profile view.")

    return None


@router.subscriber("viewed.post")
async def viewed_post_event(event: ViewedPostEvent) -> None:
    """Handles a viewed post event."""
    logger.debug(f"Received viewed post event: {event}")

    query = """
    MATCH (viewing_user:User {user_id: $viewing_user_id})
    MATCH (viewed_post:Post {post_id: $viewed_post_id})

    // Create the view event
    CREATE (view:PostView {
        view_id: $view_id,
        created_at: $created_at
    })
    CREATE (viewing_user)-[:PERFORMED]->(view)-[:VIEWED]->(viewed_post)

    // Update or create the aggregation relationship
    MERGE (viewing_user)-[r:VIEWED_POST]->(viewed_post)
    ON CREATE SET r.count = 1, r.first_viewed_at = $created_at
    ON MATCH SET r.count = r.count + 1
    SET r.last_viewed_at = $created_at

    // Update the post's view count
    SET viewed_post.view_count = COALESCE(viewed_post.view_count, 0) + 1

    // Get recent view count for analysis
    WITH viewing_user, viewed_post, view
    MATCH (viewing_user)-[:PERFORMED]->(recent_view:PostView)-[:VIEWED]->(viewed_post)
    WHERE recent_view.created_at > datetime() - duration('P30D') // Views in last 30 days

    RETURN view.id AS view_id, r.count AS user_total_views, COUNT(recent_view) AS user_recent_views, viewed_post.view_count AS post_total_views
    """
    params = {
        "viewing_user_id": event.viewing_user_id,
        "viewed_post_id": event.viewed_post_id,
        "created_at": datetime.now(UTC).isoformat(),
        "view_id": str(uuid4()),
    }
    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if record:
            logger.info(f"""
            Post view recorded. View ID: {record['view_id']}
            User's total views of this post: {record['user_total_views']}
            User's views of this post in last 30 days: {record['user_recent_views']}
            Post's total views: {record['post_total_views']}
            """)
        else:
            logger.error("Failed to record post view.")

    return None

@router.subscriber("liked.post")
async def like_post_event(event: LikedPostEvent) -> None:
    query ="""
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    MERGE (requester)-[r:LIKED {created_at: $created_at}]->(post)
    ON CREATE SET post.like_count = COALESCE(post.like_count, 0) + 1
    SET author.likes_count = COALESCE(author.likes_count, 0) + 1
    RETURN r AS like, author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": event.post_id,
                "requester_id": event.user_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to like post.")
        return None

@router.subscriber("unliked.post")
async def unlike_post_event(event: UnlikedPostEvent) -> None:
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    MATCH (requester)-[r:LIKED]->(post)
    DELETE r
    SET post.like_count = CASE WHEN post.like_count > 0 THEN post.like_count - 1 ELSE 0 END
    SET author.likes_count = CASE WHEN author.likes_count > 0 THEN author.likes_count - 1 ELSE 0 END
    RETURN author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": event.post_id,
                "requester_id": event.user_id,
            }
        )
        record = await result.single()
        if not record:
            logger.error(f"""
            Failed to unlike post {event.post_id} for user {event.user_id}.
            """)
        logger.success(f"""
        Unliked post {event.post_id} for user {event.user_id}.
        """)
        return None


@router.subscriber("added.bookmark")
async def add_bookmark_event(event: AddBookmarkEvent) -> bool:
    bookmark_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (bookmark_group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    MATCH (post:Post {post_id: $post_id})
    MATCH (author:User)-[:POSTED]->(post)

    // Check for blocks
    OPTIONAL MATCH (user)-[:BLOCKS]-(author)
    WITH user, bookmark_group, post, author, COUNT(DISTINCT author) AS block_count
    WHERE block_count = 0

    // Check for privacy
    OPTIONAL MATCH (user)-[:FOLLOWS]->(author)
    WITH user, bookmark_group, post, author, block_count, COUNT(DISTINCT author) AS follows_count
    WHERE block_count = 0 AND (NOT author.account_private OR follows_count > 0)

    // Create the bookmark
    CREATE (bookmark:Bookmark {bookmark_id: $bookmark_id, created_at: $created_at})
    MERGE (user)-[:BOOKMARKED]->(bookmark)
    MERGE (bookmark)-[:BOOKMARKS]->(post)
    MERGE (bookmark_group)-[:CONTAINS]->(bookmark)
    SET bookmark_group.bookmark_count = COALESCE(bookmark_group.bookmark_count, 0) + 1
    SET author.bookmarked_count = COALESCE(author.bookmarked_count, 0) + 1
    RETURN bookmark
    """

    params = {
        "user_id": event.user_id,
        "bookmark_group_id": event.bookmark_group_id,
        "post_id": event.post_id,
        "bookmark_id": bookmark_id,
        "created_at": created_at,
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record:
            logger.error(f"Failed to add bookmark for post {event.post_id} for user {event.user_id}.")
        logger.success(f"Added bookmark for post {event.post_id} for user {event.user_id}.")
        return True

@router.subscriber("deleted.bookmark")
async def delete_bookmark(event: DeleteBookmarkEvent) -> bool:
    query = """
    MATCH (user:User {user_id: $user_id})-[:BOOKMARKED]->(bookmark:Bookmark {bookmark_id: $bookmark_id})
    MATCH (bookmark_group:BookmarkGroup)-[:CONTAINS]->(bookmark)

    // Ensure the user is the one who created the bookmark
    OPTIONAL MATCH (bookmark)-[:BOOKMARKS]->(post:Post)
    WITH user, bookmark, bookmark_group, post, COUNT(DISTINCT bookmark) AS bookmark_count
    WHERE bookmark_count > 0

    // Delete the bookmark and its relationships
    DETACH DELETE bookmark

    // Decrement the bookmark count in the bookmark group
    SET bookmark_group.bookmark_count = CASE WHEN bookmark_group.bookmark_count > 0 THEN bookmark_group.bookmark_count - 1 ELSE 0 END
    RETURN COUNT(bookmark) AS deleted_count
    """

    params: dict[str, str] = {
        "user_id": event.user_id,
        "bookmark_id": event.bookmark_id,
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            logger.error(f"Failed to delete bookmark {event.bookmark_id} for user {event.user_id}.")
        logger.success(f"Deleted bookmark {event.bookmark_id} for user {event.user_id}.")
        return True

@router.subscriber("swiped.right")
async def swiped_right_event(event: SwipeRightEvent) -> None:
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})
    MATCH (target_user:User {user_id: $target_user_id})
    MERGE (requesting_user)-[r:SWIPED_RIGHT {created_at: $created_at}]->(target_user)
    SET target_user.swiped_right_count = COALESCE(target_user.swiped_right_count, 0) + 1
    WITH requesting_user, target_user
    MATCH (requesting_user)-[:SWIPED_RIGHT]-(target_user) AS sr_count
    RETURN COUNT(sr_count) AS swiped_right_count
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": event.requesting_user_id,
                "target_user_id": event.target_user_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        record = await result.single()
        if not record:
            logger.error(f"Failed to swipe right for user {event.target_user_id} for user {event.requesting_user_id}.")
            return None
        logger.success(f"Swiped right for user {event.target_user_id} for user {event.requesting_user_id}.")
        if record["swiped_right_count"] > 1:
            await router.broker.publish(
                topic="dating.match",
                message={
                    "user_one": event.target_user_id,
                    "user_two": event.requesting_user_id,
                }

            )

        return None

@router.subscriber("dating.match", group_id="create-db-dating-matches")
async def match_event(event: MatchEvent) -> None:
    query = """
    MATCH (user_one:User {user_id: $user_one})
    MATCH (user_two:User {user_id: $user_two})
    MERGE (user_one)-[r:DATING_MATCH {match_id: $match_id,created_at: $created_at, updated_at: $updated_at}]-(user_two)
    RETURN user_one {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .first_name,
        .last_name
        } AS user_one, user_two {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .first_name,
        .last_name
        } AS user_two,
        r.match_id AS match_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_one": event.user_one,
                "user_two": event.user_two,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        record = await result.single()
        if not record:
            logger.error(f"Failed to match user {event.user_one} with user {event.user_two}.")
            return
        logger.success(f"Matched user {event.user_one} with user {event.user_two}.")
        user_one_response = {
            "message_type": "alert-dating-match",
            "data": {
                "match_id": record["match_id"],
                "user_id": event.user_two,
                "username": record["user_two"]["username"],
                "display_name": record["user_two"]["display_name"],
                "profile_photo": record["user_two"]["profile_photo"],
                "first_name": record["user_two"]["first_name"],
                "last_name": record["user_two"]["last_name"][0].upper() + "." if record["user_two"]["last_name"] else "",
            }
        }
        user_two_response = {
            "message_type": "alert-dating-match",
            "data": {
                "match_id": record["match_id"],
                "user_id": event.user_one,
                "username": record["user_one"]["username"],
                "display_name": record["user_one"]["display_name"] if record["user_one"]["display_name"] else "",
                "profile_photo": record["user_one"]["profile_photo"] if record["user_one"]["profile_photo"] else "",
                "first_name": record["user_one"]["first_name"] if record["user_one"]["first_name"] else "",
                "last_name": record["user_one"]["last_name"][0].upper() + "." if record["user_one"]["last_name"] else "",
            }
        }

        ws_manager = WebSocketManager()
        await ws_manager.send_to_user(json.dumps(user_one_response), event.user_one)
        await ws_manager.send_to_user(json.dumps(user_two_response), event.user_two)


"""---------------- API ROUTES -----------------"""

@router.post("/api/profile/viewed")
async def viewed_profile_route(event: ViewedProfileRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> None:
    """Handles a viewed profile event."""
    await router.broker.publish(
        topic="viewed.profile",
        message={
            "viewing_user_id": verified_user.user_id,
            "viewed_user_id": event.viewed_user_id,
        }
    )

@router.post("/api/post/viewed")
async def viewed_post_route(event: ViewedPostRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> None:
    """Handles a viewed post event."""
    await router.broker.publish(
        topic="viewed.post",
        message={
            "viewing_user_id": verified_user.user_id,
            "viewed_post_id": event.viewed_post_id,
        }
    )

@router.post("/api/post/like/{post_id}", response_model=None)
async def like_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    return await router.broker.publish(
        topic="liked.post",
        message={
            "post_id": post_id,
            "user_id": verified_user.user_id,
        }
    )

@router.post("/api/post/repost/{post_id}", response_model=None)
async def repost_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    return await router.broker.publish(
        topic="reposted.post",
        message={
            "post_id": post_id,
            "user_id": verified_user.user_id,
        }
    )

@router.delete("/api/post/repost/{post_id}", response_model=None)
async def unrepost_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    return await router.broker.publish(
        topic="unreposted.post",
        message={
            "post_id": post_id,
            "user_id": verified_user.user_id,
        }
    )

@router.post("/api/bookmark", response_model=None)
async def add_bookmark_route(bookmark_request: AddBookmarkRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> None:
    return await router.broker.publish(
        topic="added.bookmark",
        message={
            "bookmark_group_id": bookmark_request.bookmark_group_id,
            "post_id": bookmark_request.post_id,
            "user_id": verified_user.user_id,
        }
    )

@router.delete("/api/bookmark/{bookmark_id}", response_model=None)
async def delete_bookmark_route(bookmark_id: str, verified_user: VerifiedUser = Depends(get_current_user)) -> None:
    return await router.broker.publish(
        topic="deleted.bookmark",
        message={
            "bookmark_id": bookmark_id,
            "user_id": verified_user.user_id,
        }
    )