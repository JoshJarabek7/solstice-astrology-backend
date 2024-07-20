"""Main file for the new backend.

TODO: AI to determine what a user looks like and use it to determine a dating taste
    recommendation property

TODO: Poaster of the month
    - At the end of each month, the user that gained the highest score gets a
        bunch of points and is visible on the leaderboards

TODO: Different recommendation engines based on user preferences
    - If they're in a relationship, don't recommend people they might be interested in

TODO: Personality assessment for people who are dating
    - Pass their personality traits to an LLM and have it output suggestions
        - Date ideas
        - Potential land mines to avoid
        - How to love each other better
TODO: Integrate an in-game currency system.
    - Potential names: 'Stardust', 'Loot', 'Points', 'Coins', 'Gold', 'Gems'
    - Keep track of how much they've had in total and how much they've spent in total
    - Subtract the total amount from the total spent to determine their balance
    - Ideas for spending currency:
        - Reveal people who have swiped right on the user's profile
        - Boost their posts
        - Reduce/remove ads
        - In-game when the game has been built
        - Wager on predictions

TODO: Discussions / Roadmap / Ideas / Bug reports
    - Discussion section on the app
        - People can give ideas, ask questions, and report bugs
        - People can also upvote ideas and bugs
        - Rankings for ideas and bugs
        - A way to mark ideas and bugs as fixed / implemented
        - User should get points if their idea gets implemented
        - Use cosine similarity to determine if two ideas or bug reports are too similar

TODO: Integrate a betting system for predictions, where you can wager in-game currency \
    on predictions.
    - Need to create a bookie system for wagers
    - Payouts when a prediction ends
    - Duration remaining of the prediction multiplier

TODO: Attach the SAS token to any media attachments in posts.
    - Determine whether or not we want to have users upload to the server
        or upload to the blob directly from the client
    - Integrate Clip to get tags about the images

TODO: TikTok backend
    - Create a TikTok style backend
    - Public Sounds to add to the video
    - It should have lots of metadata:
        - Tags
        - Description
        - Location
        - Date
        - List of audio used
            - Start time
            - End time
            - Public or Apple Music
            - URL
        - List of text overlays
            - Text
            - Size
            - Rotation
            - Font
            - Color
            - Start time
            - End time
        - Users tagged in the video
        - Transcription
            - Whisper endpoint
        - Extract text from the video
            - OCR like Tesseract
            - Do prior to adding the text overlays
            - Put it in a hash set so there's no duplicates
        - Height
        - Width
        - Embedding
            - Concatenate the text overlays, the tags, the description, captions,
                users tagged in the video, hashtags, transcription, location, date, and
                OCR text, etc.
            - K-means clustering of the embedding
    - Company logo overlays like the one in TikTok
        - Make sure the logo is not too big, moves around, and is behind the text
            overlays

TODO: Meme studio backend
    - Create a meme model
    - Create a Know Your Meme style page for each meme
    - Know Your Meme can be wikipedia-style
    - Have Meme Templates
    - Reusable and public stickers
    - Stickers should have tags and a description
    - Be able to 'see more memes like this'
    - Integrate meme taste into the recommendation engine
    - Meme collection
        - Allow users to store memes on their profile,
            rather than on their device so that they can view
            their memes all in one place
        - Allow users to upload memes to their profile,
            without necessarily create a post for it.

TODO: Change organizations to groups.
    - Check if the user is a member of the group
    - Integrate group membership into recommendations
    - Check if the group name already exists
    - Group location
    - Whether or not it's affiliated with a school
"""

import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, LiteralString, Optional, TypeVar, cast
from uuid import UUID, uuid4

import httpx
import jwt
import neo4j
import pytz
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv
from fastapi import (Depends, FastAPI, HTTPException, Query, Security,
                     WebSocket, WebSocketException, status)
from fastapi.security import OAuth2PasswordBearer
from faststream.kafka.fastapi import KafkaRouter
from jwt.algorithms import RSAAlgorithm
from loguru import logger
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, EmailStr

logger.add(sys.stderr, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", level="DEBUG")
load_dotenv()
router = KafkaRouter(os.getenv("KAFKA_CONNECTION_STRING", ""))





class KafkaMessageTypes(IntEnum):
    NOTIFICATION = 0
    BOOP = 1
    MATCH = 2
    CHAT = 3



class NotificationEvent(BaseModel):
    """Represents the event for a notification."""

    notification_type: str
    reference_id: str
    post_type: str | None = None
    target_user_id: str
    action_user_id: str
    content_preview: str | None = None
    reference_node_id: str


class NotificationGroup(BaseModel):
    notification_id: str
    notification_type: str
    reference_id: str
    content_preview: str | None = None
    post_type: str | None = None
    action_users: list[SimpleUserResponse]
    action_count: int
    is_read: bool
    updated_at: datetime


class NotificationResponse(BaseModel):
    notifications: list[NotificationGroup]
    has_more: bool
    next_cursor: datetime | None = None


"--------------- NOTIFICATIONS -----------------"


@router.get("/api/notifications", response_model=NotificationResponse)
async def get_notifications_route(
    cursor: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> NotificationResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (user:User {user_id: $user_id})-[:RECEIVED]->(n:Notification)
    WHERE n.updated_at < $cursor
    WITH n
    ORDER BY n.updated_at DESC
    LIMIT $limit

    MATCH (action_user:User)-[:ACTED_ON]->(n)
    WITH n, action_user
    ORDER BY action_user.user_id
    LIMIT 2

    RETURN {
        notification_id: n.notification_id,
        notification_type: n.notification_type,
        reference_id: n.reference_id,
        content_preview: n.content_preview,
        action_users: collect({
            user_id: action_user.user_id,
            username: action_user.username,
            display_name: action_user.display_name,
            profile_photo: action_user.profile_photo
        }),
        action_count: count(action_user)
        is_read: n.is_read,
        updated_at: n.updated_at
    } AS notification
    ORDER BY n.updated_at DESC
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,
            },
        )
        records = await result.data()

        notifications = [NotificationGroup(**record["notification"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = notifications[-1].updated_at if has_more else None

        return NotificationResponse(
            notifications=notifications,
            has_more=has_more,
            next_cursor=next_cursor,
        )


@router.post("/api/notification")
async def mark_notification_route():
    pass


"--------------- PREDICTIONS -----------------"


@router.get("/api/prediction")
async def get_predictions_route():
    pass


@router.post("/api/prediction")
async def create_prediction_route():
    pass


@router.delete("/api/prediction/{prediction_id}")
async def delete_prediction_route(prediction_id: str):
    pass


@router.get("/api/prediction/{prediction_id}")
async def get_prediction_details_route(prediction_id: str):
    pass


@router.post("/api/prediction/{prediction_id}")
async def create_prediction_answer_route(prediction_id: str):
    pass


"--------------- LEADERBOARDS -----------------"


@router.get("/api/leaderboards")
async def get_current_leaderboards_route():
    pass


@router.post("/api/leaderboards")
async def get_advanced_filtered_leaderboards_route():
    pass


@router.get("/api/leaderboards/likes")
async def get_current_likes_leaderboard_route():
    pass


@router.get("/api/leaderboards/reposts")
async def get_current_reposts_leaderboard_route():
    pass


@router.get("/api/leaderboards/prior/likes")
async def get_prior_likes_leaderboard_route():
    pass


@router.get("/api/leaderboards/prior/reposts")
async def get_prior_reposts_leaderboard_route():
    pass


"--------------- PERSONALITY -----------------"

question_mapping = {}
with Path("scores.json").open() as f:
    question_mapping_string = f.read()
    question_mapping = json.loads(question_mapping_string)


async def calculate_trait_scores(
    user_answers: dict[str, bool],
) -> dict[str, float]:
    """Calculate the trait scores for a user based on their answers and weights.

    Args:
        user_answers (dict[str, bool]): question_id key and bool value

    Returns:
        dict[str, float]: The trait scores for the user.

    Example:
        >>> await calculate_trait_scores(
        ...     {
        ...         "Do you ever make unnecessary and loud noises when
                        you're home alone?": True
        ...     },
        ...     {"Introversion/Extraversion": {"Thinking/Feeling": 1.0}},
        ... )
        {"Introversion/Extraversion": 0.0}
    """
    trait_scores: dict[str, dict[str, float]] = {}
    for question_id in user_answers:
        answer = user_answers[question_id]
        if question_id not in question_mapping:
            continue
        for trait in cast(
            dict[str, str | dict[str, float]],
            question_mapping[question_id],
        ):
            if trait == "question":
                continue
            if trait not in trait_scores:
                trait_scores[trait] = {
                    "cumulative_score": 0.0,
                    "count": 0,
                }
            if answer:
                trait_scores[trait]["cumulative_score"] += cast(
                    float,
                    question_mapping[question_id][trait]["presence_given_yes"],
                )
                trait_scores[trait]["count"] += 1
            else:
                trait_scores[trait]["cumulative_score"] += cast(
                    float,
                    question_mapping[question_id][trait]["presence_given_no"],
                )
                trait_scores[trait]["count"] += 1
    normalized_scores: dict[str, float] = {}
    for trait in trait_scores:
        trait_data = trait_scores[trait]
        if trait_data["count"] > 0:
            raw_score = trait_data["cumulative_score"] / trait_data["count"]
            weight = 4
            median_value = 0.5
            if raw_score > median_value:
                weighted_score = median_value + (raw_score - median_value) * weight
            else:
                weighted_score = median_value - (median_value - raw_score) * weight
            normalized_score = min(max(weighted_score, 0.0), 1.0)
        else:
            normalized_score: float = 0.0
        normalized_scores[trait] = float(normalized_score)
    return normalized_scores


# async def get_trait_scores_paired(
#     user1_id: str,
#     user2_id: str,
# ) -> tuple[dict[str, float], dict[str, float]]:
#     """Compare the trait scores for two users based on their answers and weights.

#     Args:
#         user1_id (str): The ID of the first user.
#         user2_id (str): The ID of the second user.

#     Returns:
#         tuple[dict[str, float], dict[str, float]]: The trait scores for the two users.
#     """
#     users_answers = await get_both_user_answers(user1_id, user2_id)

#     user1_scores = await calculate_trait_scores(users_answers[0])
#     user2_scores = await calculate_trait_scores(users_answers[1])

#     return user1_scores, user2_scores


# async def get_trait_scores_self(
#     user_id: str,
# ) -> dict[str, float]:
#     """Get the trait scores for a user.

#     Args:
#         user_id (str): The ID of the user.

#     Returns:
#         dict[str, float]: The trait scores for the user.
#     """
#     users_answers = await get_user_answers(user_id)
#     return await calculate_trait_scores(users_answers)


@router.get("/api/personality/{user_id}")
async def get_personality_profile_route(user_id: str):
    pass


@router.post("/api/personality/question/{question_id}")
async def answer_personality_question_route(question_id: str):
    pass


@router.delete("/api/personality/question/{question_id}")
async def delete_personality_question_answer_route(question_id: str):
    pass


"--------------- CHAT -----------------"


class ConversationType(IntEnum):
    GENERAL_ONE_ON_ONE = 0
    GENERAL_GROUP = 1
    DATING_ONE_ON_ONE = 2

class ChatActionType(IntEnum):
    MESSAGE = 0
    TYPING = 1
    REACTION = 2
    USER_JOINED = 3
    USER_LEFT = 4
    OPEN_CONVERSATION = 5


async def mark_conversation_as_read(conversation_id: str, user_id: str):
    query = """
    MATCH (u:User {user_id: $user_id})-[r:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    SET r.last_read = datetime()
    """
    await driver.session().run(query, {"conversation_id": conversation_id, "user_id": user_id})


async def add_message_to_existing_conversation(
    conversation_id: str,
    sender_id: str,
    message: CreateConversationInitialMessageRequest,
) -> Conversation:
    message_id = str(uuid4())
    current_time = datetime.now(UTC).isoformat()

    query = """
    MATCH (c:Conversation {conversation_id: $conversation_id})
    MATCH (sender:User {user_id: $sender_id})
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        attached_media_url: $attached_media_url,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(m)-[:IN]->(c)
    SET c.updated_at = $updated_at
    WITH c, m
    OPTIONAL MATCH (attached_post:Post {post_id: $attached_post_id})
    FOREACH (post IN CASE WHEN attached_post IS NOT NULL THEN [attached_post] ELSE [] END |
        CREATE (m)-[:ATTACHED_TO_POST]->(post)
    )
    RETURN c, m
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_id": message_id,
                "content": message.content,
                "attached_media_url": message.attached_media_url,
                "created_at": message.created_at.isoformat(),
                "updated_at": current_time,
                "attached_post_id": message.attached_post_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add message to existing conversation.",
            )

        # Fetch and return the full conversation details
        return await get_conversation_details(conversation_id)


async def get_conversation_details(conversation_id: str) -> Conversation:
    query = """
    MATCH (c:Conversation {conversation_id: $conversation_id})
    OPTIONAL MATCH (c)<-[:PARTICIPATES_IN]-(p:User)
    OPTIONAL MATCH (c)<-[:ADMIN_OF]-(a:User)
    WITH c,
         collect(DISTINCT {
             user_id: p.user_id,
             username: p.username,
             display_name: p.display_name,
             profile_photo: p.profile_photo
         }) AS participants,
         collect(DISTINCT {
             user_id: a.user_id,
             username: a.username,
             display_name: a.display_name,
             profile_photo: a.profile_photo
         }) AS admins
    RETURN {
        conversation_id: c.conversation_id,
        conversation_type: c.conversation_type,
        title: c.title,
        image_url: c.image_url,
        participants: participants,
        admins: admins,
        created_at: c.created_at,
        updated_at: c.updated_at
    } AS conversation
    """
    async with driver.session() as session:
        result = await session.run(query, {"conversation_id": conversation_id})
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation_data = record["conversation"]
        return Conversation(**conversation_data)


@router.delete("/api/chat/conversation/{conversation_id}")
async def delete_conversation_route(conversation_id: str):
    pass


@router.delete("/api/chat/conversation/{conversation_id}/message/{message_id}")
async def delete_conversation_message_route(conversation_id: str, message_id: str):
    pass


@router.post("/api/chat/{conversation_id}/message", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    message: SendMessageRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> MessageResponse:
    async with driver.session() as session:
        # Check if the user is a participant in the conversation
        participant_check_query = """
        MATCH (u:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
        RETURN c
        """
        result = await session.run(
            participant_check_query,
            {"user_id": str(verified_user.user_id), "conversation_id": str(conversation_id)},
        )
        if not await result.single():
            raise HTTPException(status_code=403, detail="You are not a participant in this conversation")

        # Create the message
        message_id = uuid4()
        created_at = datetime.now(UTC)

        create_message_query = """
        MATCH (sender:User {user_id: $sender_id})
        MATCH (c:Conversation {conversation_id: $conversation_id})
        CREATE (m:Message {
            message_id: $message_id,
            content: $content,
            created_at: $created_at,
            attached_media_urls: $attached_media_urls
        })
        CREATE (sender)-[:SENT]->(m)-[:IN]->(c)

        WITH m, c, sender

        OPTIONAL MATCH (attached_post:Post {post_id: $attached_post_id})
        FOREACH (post IN CASE WHEN attached_post IS NOT NULL THEN [attached_post] ELSE [] END |
            CREATE (m)-[:ATTACHED_TO_POST]->(post)
        )

        WITH m, c, sender

        OPTIONAL MATCH (reply_to:Message {message_id: $reply_to_message_id})
        FOREACH (reply IN CASE WHEN reply_to IS NOT NULL THEN [reply_to] ELSE [] END |
            CREATE (m)-[:REPLY_TO_MESSAGE]->(reply)
        )

        SET c.updated_at = $created_at

        RETURN m.message_id AS message_id,
               m.content AS content,
               sender.user_id AS sender_id,
               sender.username AS sender_username,
               m.created_at AS created_at,
               m.attached_media_urls AS attached_media_urls
        """

        result = await session.run(
            create_message_query,
            {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "sender_id": str(verified_user.user_id),
                "content": message.content,
                "created_at": created_at.isoformat(),
                "attached_post_id": str(message.attached_post_id) if message.attached_post_id else None,
                "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
                "attached_media_urls": message.attached_media_urls,
            },
        )

        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create message")

        # Publish to "chat.message.new" topic
        await router.broker.publish(
            topic="chat.message.new",
            message={
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
                "sender_id": str(verified_user.user_id),
                "content": message.content,
                "created_at": created_at.isoformat(),
                "attached_post_id": str(message.attached_post_id) if message.attached_post_id else None,
                "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
                "attached_media_urls": message.attached_media_urls,
            },
        )

        return MessageResponse(
            message_id=UUID(record["message_id"]),
            content=record["content"],
            sender_id=UUID(record["sender_id"]),
            sender_username=record["sender_username"],
            created_at=record["created_at"],
            attached_post_id=message.attached_post_id,
            reply_to_message_id=message.reply_to_message_id,
            attached_media_urls=record["attached_media_urls"],
        )


"--------------- STATS -----------------"


@router.get("/api/stats/user/{user_id}")
async def get_user_stats_route(user_id: str):
    pass


"--------------- DATING -----------------"


class DatingSwipeEvent(BaseModel):
    swiped_right: bool
    requesting_user_id: str
    target_user_id: str


def calculate_distance(location1: tuple[float, float], location2: tuple[float, float]) -> float:
    """Calculate the distance between two points on Earth in miles."""
    r = 3959  # Earth's radius in miles (instead of 6371 for kilometers)

    lat1, lon1 = map(radians, location1)
    lat2, lon2 = map(radians, location2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = r * c
    return round(distance, 2)  # Round to 2 decimal places


@router.get("/api/dating/profile/{user_id}")
async def get_dating_profile_route(user_id: str, verified_user: VerifiedUser = Depends(get_current_user)):
    """Get the dating profile for a user."""
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (user)-[:BLOCKS]-(requester)
    WITH user, requester, COUNT(requester) AS block_count
    WHERE block_count = 0
    WITH user, requester

    RETURN user {
        .user_id,
        .display_name.
        .first_name,
        .last_name,
        .profile_photo,
        .account_private,
        .username,
        .recent_location,
        .dating_photos,
        .dating_bio,
        .height,
        .gender,
        .sexual_orientation,
        .relationship_status,
        .religion,
        .highest_education_level,
        .looking_for,
        .has_children,
        .wants_children,
        .has_tattoos,
        .show_gender,
        .show_sexual_orientation,
        .show_relationship_status,
        .show_religion,
        .show_education,
        .show_looking_for,
        .show_schools,
        .show_has_children,
        .show_wants_children
        } AS user_data, requester.recent_location AS requester_recent_location
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or access denied",
            )
        user_data = record["user_data"]
        requester_location = record["requester_recent_location"]
        user_location = user_data["recent_location"]
        distance = None
        if requester_location and user_location:
            distance = calculate_distance(requester_location, user_location)

        response = DetailedDatingProfileResponse(
            user_id=user_data["user_id"],
            display_name=user_data["display_name"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            profile_photo=user_data["profile_photo"],
            account_private=user_data["account_private"],
            username=user_data["username"],
            distance=distance,
            dating_photos=user_data["dating_photos"],
            dating_bio=user_data["dating_bio"],
            height=user_data["height"],
            has_tattoos=user_data["has_tattoos"],
        )
        if user_data["show_gender"]:
            response.gender = user_data["gender"]
        if user_data["show_sexual_orientation"]:
            response.sexual_orientation = user_data["sexual_orientation"]
        if user_data["show_relationship_status"]:
            response.relationship_status = user_data["relationship_status"]
        if user_data["show_religion"]:
            response.religion = user_data["religion"]
        if user_data["show_looking_for"]:
            response.looking_for = user_data["looking_for"]
        if user_data["highest_education_level"]:
            response.highest_education_level = user_data["highest_education_level"]
        if user_data["show_has_children"]:
            response.has_children = user_data["has_children"]
        if user_data["show_wants_children"]:
            response.wants_children = user_data["wants_children"]
        return response


# @router.get("/api/dating/matches")
# async def get_dating_matches_route(verified_user: VerifiedUser = Depends(get_current_user)):


@router.get("/api/dating/feed", response_model=list[DetailedDatingProfileResponse])
async def get_dating_feed_route(
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> list[DetailedDatingProfileResponse]:
    query = """
    // Match the requesting user
    MATCH (user:User {user_id: $user_id})
    MATCH user.dating_active = true

    // Match potential dating profiles
    MATCH (potential:User)
    WHERE potential.dating_active = true
    AND potential.user_id <> user.user_id

    // Privacy checks
    WHERE NOT (user)-[:BLOCKS]-(potential)
    AND NOT (user)-[:SWIPED_LEFT]->(potential)
    AND NOT (user)-[:SWIPED_RIGHT]->(potential)
    AND NOT (user)-[:MATCH]->(potential)

    // Location-based filtering
    WITH user, potential
        point.distance(point({latitude: user.recent_location[0], longitude: user.recent_location[1]}),
            point({latitude: potential.recent_location[0], longitude: potential.recent_location[1]})) / 1609.34AS distance_miles
    WHERE distance_miles <= user.max_distance

    // Preference-based filtering
    WHERE (NOT potential.show_gender OR potential.gender IN user.gender_preferences OR size(user.gender_preferences) = 0)
        AND (NOT potential.show_has_children OR potential.has_children IN user.has_children_preferences OR size(user.has_children_preferences) = 0)
        AND (NOT potential.show_wants_children OR potential.wants_children IN user.wants_children_preferences OR size(user.wants_children_preferences) = 0)
        AND (NOT potential.show_education OR potential.highest_education_level IN user.education_level_preferences OR size(user.education_level_preferences) = 0)
        AND (NOT potential.show_religion OR potential.religion IN user.religion_preferences OR size(user.religion_preferences) = 0)
        AND (NOT potential.show_sexual_orientation OR potential.sexual_orientation IN user.sexual_orientation_preferences OR size(user.sexual_orientation_preferences) = 0)
        AND (NOT potential.show_relationship_status OR potential.relationship_status IN user.relationship_status_preferences OR size(user.relationship_status_preferences) = 0)
        AND (NOT potential.show_looking_for OR potential.looking_for IN user.looking_for_preferences OR size(user.looking_for_preferences) = 0)
        AND (toInteger(potential.height) >= user.minimum_height OR user.minimum_height = 0)
        AND (toInteger(potential.height) <= user.maximum_height OR user.maximum_height = 0)

    // Calculate age
    WITH user, potential, distance_miles,
         duration.between(date(potential.birth_datetime_utc), date()).years AS age
    WHERE age >= user.minimum_age AND age <= user.maximum_age

    // Prioritization factors
    OPTIONAL MATCH (user)-[:FOLLOWS]->(potential)
    OPTIONAL MATCH (potential)-[:FOLLOWS]->(user)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(potential)
    OPTIONAL MATCH (potential)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(user)
    WITH user, potential, distance_miles, age,
         CASE WHEN (user)-[:FOLLOWS]->(potential) THEN 10 ELSE 0 END +
         CASE WHEN (potential)-[:FOLLOWS]->(user) THEN 8 ELSE 0 END +
         CASE WHEN (user)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(potential) THEN 5 ELSE 0 END +
         CASE WHEN (potential)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(user) THEN 4 ELSE 0 END +
         5 * EXP(-distance_miles / 50) + // Prioritize closer profiles
         10 * EXP(-(duration.inSeconds(datetime() - potential.last_seen).hours / 24)) AS score  // Recency score

    WHERE potential.last_seen < $cursor

    RETURN potential {
        .user_id,
        .display_name,
        .first_name,
        .last_name,
        .profile_photo,
        .account_private,
        .username,
        recent_location: potential.recent_location,
        .dating_photos,
        .dating_bio,
        .height,
        gender: CASE WHEN potential.show_gender THEN potential.gender ELSE null END,
        sexual_orientation: CASE WHEN potential.show_sexual_orientation THEN potential.sexual_orientation ELSE null END,
        relationship_status: CASE WHEN potential.show_relationship_status THEN potential.relationship_status ELSE null END,
        religion: CASE WHEN potential.show_religion THEN potential.religion ELSE null END,
        highest_education_level: CASE WHEN potential.show_education THEN potential.highest_education_level ELSE null END,
        looking_for: CASE WHEN potential.show_looking_for THEN potential.looking_for ELSE null END,
        has_children: CASE WHEN potential.show_has_children THEN potential.has_children ELSE null END,
        wants_children: CASE WHEN potential.show_wants_children THEN potential.wants_children ELSE null END,
        .has_tattoos,
    } AS potential_data, distance_miles, score

    ORDER BY score DESC, potential.last_seen DESC
    LIMIT $limit
    """  # noqa: E501

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "cursor": cursor.isoformat() if cursor else datetime.now(UTC).isoformat(),
                "limit": limit,
            },
        )

        records = await result.data()

        dating_profiles: list[DetailedDatingProfileResponse] = []
        for record in records:
            profile_data = record["potential_data"]
            profile_data["distance"] = record["distance_miles"]
            dating_profiles.append(DetailedDatingProfileResponse(**profile_data))

        return dating_profiles


class DatingMatchDeleteRequest(BaseModel):
    match_id: str
    requesting_user_id: str


@router.delete("/api/dating/matches/{match_id}")
async def delete_dating_match_route(match_id: str, verified_user: VerifiedUser = Depends(get_current_user)):
    """Delete a dating match."""
    await router.broker.publish(
        topic="dating.delete_match",
        message={
            "match_id": match_id,
            "requesting_user_id": verified_user.user_id,
        },
    )


@router.subscriber("dating.delete_match")
async def delete_match_event(event: DatingMatchDeleteRequest) -> None:
    """TOPIC: dating.delete_match - Subscriber for dating match delete events."""
    match_id = event.match_id
    requesting_user_id = event.requesting_user_id
    query = """
    MATCH (u1:User {user_id: $requesting_user_id})-[m:MATCH {match_id: $match_id}]->(u2:User)
    RETURN m.match_id AS match_id, u2.user_id AS other_user_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "match_id": match_id,
            },
        )
        record = await result.single()
        if not record:
            logger.error(f"Match not found or user {requesting_user_id} not authorized to delete match {match_id}")
            return

        other_user_id = record["other_user_id"]

        delete_match_query = """
        MATCH (u1:User {user_id: $requesting_user_id})-[m:MATCH {match_id: $match_id}]-(u2:User {user_id: $other_user_id})
        DELETE m
        """

        await session.run(
            delete_match_query,
            {"requesting_user_id": requesting_user_id, "match_id": match_id, "other_user_id": other_user_id},
        )

        delete_conversation_query = """
        MATCH (u1:User {user_id: $requesting_user_id})-[:PARTICIPATES_IN]->(conv:Conversation {conversation_type: $conversation_type})<-[:PARTICIPATES_IN]-(u2:User {user_id: $other_user_id})
        OPTIONAL MATCH (m:Message)-[:IN]->(conv)
        DETACH DELETE m, conv
        """
        await session.run(
            delete_conversation_query,
            {
                "reqeuesting_user_id": requesting_user_id,
                "other_user_id": other_user_id,
                "conversation_type": ConversationType.DATING_ONE_ON_ONE.value,
            },
        )

@router.websocket("/ws/general")
async def websocket_general_endpoint(
    websocket: WebSocket,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """WebSocket endpoint for general chat."""
    logger.info("Received websocket connection for general chat")
    general_manager = GeneralManager()
    socket_id = await general_manager.connect(websocket, verified_user.user_id)
    try:
        while True:
            data = GeneralKafkaWebsocketMessage(**await websocket.receive_json())
            await router.broker.publish(
                topic=data.topic,
                message=data.model_dump_json(),
            )
    except WebSocketException as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await general_manager.disconnect(verified_user.user_id, socket_id)


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """WebSocket endpoint for chat."""
    logger.info(f"Received websocket connection for conversation {conversation_id}")
    chat_manager = ChatManager()
    socket_id = await chat_manager.connect(websocket, conversation_id, verified_user.user_id)
    try:
        while True:
            data = ChatActionRequest(**await websocket.receive_json())

            if data.action_type == ChatActionType.TYPING:
                await router.broker.publish(
                    topic="chat.typing",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.MESSAGE:
                await router.broker.publish(
                    topic="chat.message",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.USER_JOINED:
                await router.broker.publish(
                    topic="chat.user_joined",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.USER_LEFT:
                await router.broker.publish(
                    topic="chat.user_left",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.OPEN_CONVERSATION:
                await router.broker.publish(
                    topic="chat.open_conversation",
                    message=data.model_dump_json(),
                )
    except WebSocketException as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await chat_manager.disconnect(conversation_id, verified_user.user_id, socket_id)


"--------------- STORIES -----------------"

"--------------- BOOPS -----------------"


class BoopResponse(BaseModel):
    boop_id: str
    booped_user_id: str
    total_boops: int
    created_at: datetime
    updated_at: datetime
    is_your_turn: bool
    is_new_unread_boop: bool


class BoopedEvent(BaseModel):
    boop_id: str
    booped_user_id: str
    total_boops: int
    created_at: datetime
    updated_at: datetime
    is_your_turn: bool
    is_new_unread_boop: bool


@router.post("/api/boop/{target_user_id}", response_model=BoopResponse)
async def send_boop_route(target_user_id: str, verified_user: VerifiedUser = Depends(get_current_user)) -> BoopResponse:
    async with driver.session() as session:
        # Check if the users can interact (not blocked, follows if private)
        can_interact_query = """
        MATCH (sender:User {user_id: $sender_id}), (receiver:User {user_id: $receiver_id})
        WHERE NOT (sender)-[:BLOCKS]-(receiver)
        AND (NOT receiver.account_private OR (sender)-[:FOLLOWS]->(receiver))
        RETURN COUNT(*) > 0 AS can_interact
        """
        result = await session.run(
            can_interact_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
            },
        )
        record = await result.single()
        if not record or not record["can_interact"]:
            raise HTTPException(status_code=403, detail="You cannot boop someone who you cannot interact with")

        # Check if it's the sender's turn to boop
        turn_check_query = """
        MATCH (sender:User {user_id: $sender_id})-[boop:BOOP_RELATIONSHIP]-(receiver:User {user_id: $receiver_id})
        RETURN boop.last_booper_id <> $sender_id AS is_sender_turn
        """
        result = await session.run(
            turn_check_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to check turn")
        if not record["is_sender_turn"]:
            raise HTTPException(status_code=403, detail="It's not your turn to boop")

        # Create or update the BOOP_RELATIONSHIP
        boop_query = """
        MATCH (sender:User {user_id: $sender_id})
        MATCH (receiver:User {user_id: $receiver_id})
        MERGE (sender)-[boop:BOOP_RELATIONSHIP]-(receiver)
        ON CREATE SET
            boop.boop_id = $boop_id,
            boop.total_boops = 1,
            boop.created_at = $boop_created_at,
            boop.updated_at = $boop_updated_at,
            boop.last_booper_id = $sender_id,
            receiver.unread_boops = COALESCE(receiver.unread_boops, 0) + 1
        ON MATCH SET
            boop.total_boops = boop.total_boops + 1,
            boop.updated_at = $boop_updated_at,
            boop.last_booper_id = $sender_id,
            receiver.unread_boops = CASE
                WHEN boop.last_booper_id <> $sender_id
                THEN COALESCE(receiver.unread_boops, 0) + 1
                ELSE receiver.unread_boops
            END
        RETURN boop.boop_id AS boop_id,
               sender.user_id AS booper_id,
               sender.username AS booper_username,
               boop.total_boops AS total_boops,
               boop.created_at AS boop_created_at,
               boop.updated_at AS boop_updated_at,
               boop.last_booper_id AS last_booper_id,
               receiver.unread_boops AS receiver_unread_boops
        """
        result = await session.run(
            boop_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
                "boop_id": str(uuid4()),
                "boop_created_at": datetime.now(UTC),
                "boop_updated_at": datetime.now(UTC),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create boop")
        is_your_turn = record["last_booper_id"] != str(verified_user.user_id)
        is_new_unread_boop = record["receiver_unread_boops"] > 0
        return BoopResponse(
            boop_id=record["boop_id"],
            booped_user_id=target_user_id,
            total_boops=record["total_boops"],
            created_at=record["boop_created_at"],
            updated_at=record["boop_updated_at"],
            is_your_turn=is_your_turn,
            is_new_unread_boop=is_new_unread_boop,
        )


"--------------- EVENTS -----------------"

"""
We're going to have an API route for creating a conversation,
but once it's been created, everything else will be handled via
websockets.

"""


@router.subscriber("chat.message.new")
async def chat_message(event: ChatActionRequest):
    if event.action_type != ChatActionType.MESSAGE:
        raise HTTPException(status_code=400, detail="Invalid action type")

    if not isinstance(event.action_data, ChatActionMessageRequest):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    if not event.action_data.created_at:
        raise HTTPException(status_code=400, detail="Invalid message creation time")

    query = """
    MATCH (conversation:Conversation {conversation_id: $conversation_id})
    MATCH (sender:User {user_id: $sender_id})
    CREATE (message:Message {
        message_id: $message_id,
        content: $content,
        attached_media_url: $attached_media_url,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(message)-[:IN]->(conversation)
    FOREACH (reply_id IN CASE WHEN $reply_to_id IS NOT NULL THEN [$reply_to_id] ELSE [] END |
        MATCH (reply_to:Message {message_id: reply_id})
        CREATE (message)-[:REPLY_TO_MESSAGE]->(reply_to)
    )
    FOREACH (attached_post_id IN CASE WHEN $attached_post_id IS NOT NULL THEN [$attached_post_id] ELSE [] END |
        MATCH (post:Post {post_id: attached_post_id})
        CREATE (message)-[:ATTACHED_TO_POST]->(post)
    )
    RETURN message
    """

    async with driver.session() as session:
        message_id = str(uuid4())
        result = await session.run(
            query,
            {
                "message_id": message_id,
                "conversation_id": event.conversation_id,
                "sender_id": event.user_id,
                "content": event.action_data.content,
                "attached_media_url": event.action_data.attached_media_url,
                "created_at": event.action_data.created_at,
                "reply_to_id": event.action_data.reply_to_id,
                "attached_post_id": event.action_data.attached_post_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Message not found")
        response = ChatActionResponse(**record["message"])
        chat_manager = ChatManager()
        await chat_manager.broadcast(response, event.conversation_id, event.user_id)


@router.subscriber("chat.typing")
async def chat_typing(event: ChatActionRequest):
    if event.action_type != ChatActionType.TYPING:
        raise HTTPException(status_code=400, detail="Invalid action type")

    if not isinstance(event.action_data, ChatActionTyping):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    outbound = ChatActionResponse(
        conversation_id=event.conversation_id,
        user_id=event.user_id,
        action_type=ChatActionType.TYPING,
        action_data=event.action_data,
    )
    chat_manager = ChatManager()
    await chat_manager.broadcast(outbound, event.conversation_id, event.user_id)


@router.subscriber("chat.user_joined")
async def chat_user_joined(event: ChatActionRequest):
    if event.action_type != ChatActionType.USER_JOINED:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})
    RETURN user.user_id AS user_id, user.username AS username, user.display_name AS display_name, user.profile_photo AS profile_photo
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.action_data,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = SimpleUserResponse(**record)
        chat_manager = ChatManager()
        # When they're added, the user_id is the one who added them
        # The action_data is the user added
        await chat_manager.broadcast(
            ChatActionResponse(
                conversation_id=event.conversation_id,
                user_id=event.action_data,
                action_type=ChatActionType.USER_JOINED,
                action_data=response,
            ),
            event.conversation_id,
            event.user_id,
        )


@router.subscriber("chat.user_left")
async def chat_user_left(event: ChatActionRequest):
    if event.action_type != ChatActionType.USER_LEFT:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})
    RETURN user.user_id AS user_id, user.username AS username, user.display_name AS display_name, user.profile_photo AS profile_photo
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.action_data,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = SimpleUserResponse(**record)
        chat_manager = ChatManager()
        await chat_manager.broadcast(
            ChatActionResponse(
                conversation_id=event.conversation_id,
                user_id=event.user_id,
                action_type=ChatActionType.USER_LEFT,
                action_data=response,
            ),
            event.conversation_id,
            event.user_id,
        )


@router.subscriber("chat.open_conversation")
async def chat_open_conversation(event: ChatActionRequest):
    """Mark the conversation notifications as read and sync across user's devices."""
    if event.action_type != ChatActionType.OPEN_CONVERSATION:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})-[:RECEIVED]->(n:Notification)
    WHERE n.reference_id = $conversation_id AND n.notification_type = 'NEW_MESSAGE' AND n.is_read = false
    SET n.is_read = true, n.updated_at = datetime()
    RETURN n.notification_id AS notification_id, n.updated_at AS updated_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.user_id,
                "conversation_id": event.conversation_id,
            },
        )
        records = await result.data()

        if records:
            # Only update the user's other devices if notifications were marked as read
            notification_manager = GeneralManager()
            updated_notifications = [
                NotificationGroup(
                    notification_id=record["notification_id"],
                    notification_type="NEW_MESSAGE",
                    reference_id=event.conversation_id,
                    is_read=True,
                    updated_at=record["updated_at"],
                    action_users=[],  # We don't need to send this information
                    action_count=0,  # We don't need to send this information
                    content_preview=None,  # We don't need to send this information
                )
                for record in records
            ]
            await notification_manager.broadcast(
                NotificationResponse(notifications=updated_notifications, has_more=False, next_cursor=None).model_dump_json(),
                event.user_id,
            )

    # Acknowledge the open conversation action only to the user who opened it
    chat_manager = ChatManager()
    await chat_manager.send_to_user(
        ChatActionResponse(
            conversation_id=event.conversation_id,
            user_id=event.user_id,
            action_type=ChatActionType.OPEN_CONVERSATION,
            action_data="Conversation opened and notifications marked as read",
        ),
        event.conversation_id,
        event.user_id,
    )


class MajorSectionViewed(BaseModel):
    section: str
    user_id: str


class MajorSectionViewedResponse(MajorSectionViewed):
    updated_at: datetime


@router.post("/api/user/major-section/{section}", response_model=None)
async def user_viewed_major_section_route(section: str, verified_user: VerifiedUser = Depends(get_current_user)):
    await router.broker.publish(
        topic="major-section.viewed",
        message={
            "section": section,
            "user_id": verified_user.user_id,
        },
    )


@router.subscriber("major-section.viewed")
async def user_viewed_boops_page_event(event: MajorSectionViewed) -> None:
    """Update the last time a user viewed a major section."""
    general_manager = GeneralManager()

    query = f"""
    MATCH (user:User {{user_id: $user_id}})
    SET user.last_checked_{event.section} = $last_checked
    RETURN user.last_checked_{event.section} as updated_at
    """
    last_checked = datetime.now(UTC)
    literal_query = cast(LiteralString, query)
    async with driver.session() as session:
        result = await session.run(
            literal_query,
            {
                "user_id": event.user_id,
                "last_checked": last_checked.isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = MajorSectionViewedResponse(
            section=event.section,
            user_id=event.user_id,
            updated_at=last_checked,
        )
        await general_manager.broadcast(
            response.model_dump_json(),
            event.user_id,
        )


# @router.subscriber("create-or-update-notification")
# async def create_or_update_notification(event: NotificationEvent):
#     query = """
#     MERGE (n:Notification {notification_type: $notification_type, reference_id: $reference_id})
#     ON CREATE SET
#         n.notification_id = apoc.create.uuid(),
#         n.content_preview = $content_preview,
#         n.post_type = $post_type,
#         n.action_count = 1,
#         n.is_read = false,
#         n.updated_at = datetime()
#     ON MATCH SET
#         n.action_count = n.action_count + 1,
#         n.is_read = false,
#         n.updated_at = datetime()

#     WITH n

#     MATCH (target_user:User {user_id: $target_user_id})
#     MERGE (target_user)-[:RECEIVED]->(n)

#     WITH n

#     MATCH (action_user:User {user_id: $action_user_id})
#     MERGE (action_user)-[:ACTED_ON]->(n)

#     RETURN n as notification
#     """
#     async with driver.session() as session:
#         result = await session.run(
#             query,
#             {
#                 "notification_type": event.notification_type,
#                 "reference_id": event.reference_id,
#                 "content_preview": event.content_preview,
#                 "post_type": event.post_type,
#                 "target_user_id": event.target_user_id,
#                 "action_user_id": event.action_user_id,
#             },
#         )
#         record = await result.single()
#         if not record:
#             raise HTTPException(status_code=404, detail="Notification not found")
#         response = NotificationResponse(**record["notification"])
#         notification_manager = NotificationManager()
#         await notification_manager.broadcast(response, event.target_user_id)

app = FastAPI(lifespan=router.lifespan_context)

app.include_router(router)
