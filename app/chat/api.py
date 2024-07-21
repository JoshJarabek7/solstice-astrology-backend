import json
from typing import Any

from fastapi import Depends
from faststream.kafka.fastapi import KafkaRouter

from app.chat.db import (create_dating_chat, create_dating_chat_message,
                         create_group_chat, create_group_chat_message,
                         create_private_chat, create_private_chat_message,
                         is_post_accessible_to_user)
from app.chat.schemas import (ChatCreatedEvent, ConversationMessageEvent,
                              CreateDatingChatRequest, CreateGroupChatRequest,
                              CreatePrivateChatRequest, PostPreview,
                              SendMessageRequest)
from app.notifications.ws import WebSocketManager
from app.shared.auth import get_current_user
from app.shared.neo4j import driver
from app.users.schemas import VerifiedUser

router = KafkaRouter()


@router.post("/api/chat/conversation/group/create", response_model=dict[str, str])
async def create_group_chat_route(request: CreateGroupChatRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> dict[str, str]:
    """Handles a create conversation request."""
    res = await create_group_chat(request, verified_user.user_id)
    conversation_id = res["conversation_id"]
    message_id = res["message_id"]
    await router.broker.publish(
        topic="chat.group.created",
        message=ChatCreatedEvent(
            conversation_id=conversation_id,
            message_id=message_id,
            conversation_type=request.conversation_type,
            participants=request.participants,
            initial_message=request.initial_message,
        ).model_dump(),
    )
    return {
        "conversation_id": conversation_id,
    }

@router.post("/api/chat/conversation/private/create", response_model=dict[str, str])
async def create_single_chat_route(request: CreatePrivateChatRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> dict[str, str]:
    res = await create_private_chat(request, verified_user.user_id)
    conversation_id = res["conversation_id"]
    message_id = res["message_id"]
    await router.broker.publish(
        topic="chat.private.created",
        message=ChatCreatedEvent(
            conversation_id=conversation_id,
            message_id=message_id,
            conversation_type=request.conversation_type,
            participants=request.participants,
            initial_message=request.initial_message,
        ).model_dump(),
    )
    return {
        "conversation_id": conversation_id,
    }

@router.post("/api/chat/conversation/dating/create", response_model=dict[str, str])
async def create_dating_chat_route(request: CreateDatingChatRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> dict[str, str]:
    res = await create_dating_chat(request, verified_user.user_id)
    conversation_id = res["conversation_id"]
    message_id = res["message_id"]
    await router.broker.publish(
        topic="chat.dating.created",
        message=ChatCreatedEvent(
            conversation_id=conversation_id,
            message_id=message_id,
            conversation_type=request.conversation_type,
            participants=request.participants,
            initial_message=request.initial_message,
        ).model_dump(),
    )
    return {
        "conversation_id": conversation_id,
    }

@router.post("/api/chat/conversation/group/send-message", response_model=ConversationMessageEvent)
async def send_group_chat_message_route(request: SendMessageRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> ConversationMessageEvent:
    res = await create_group_chat_message(request.conversation_id, request.sender_id, request.content, request.attached_post_id, request.attached_media_urls, request.reply_to_message_id)
    await router.broker.publish(
        topic="chat.group.message.created",
        message=res.model_dump_json()
    )
    return res

@router.post("/api/chat/conversation/private/send-message", response_model=ConversationMessageEvent)
async def send_private_chat_message_route(request: SendMessageRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> ConversationMessageEvent:
    res = await create_private_chat_message(request.conversation_id, request.sender_id, request.content, request.attached_post_id, request.attached_media_urls, request.reply_to_message_id)
    await router.broker.publish(
        topic="chat.private.message.created",
        message=res.model_dump_json()
    )
    return res

@router.post("/api/chat/conversation/dating/send-message", response_model=ConversationMessageEvent)
async def send_dating_chat_message_route(request: SendMessageRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> ConversationMessageEvent:
    res = await create_dating_chat_message(request.conversation_id, request.sender_id, request.content, request.attached_post_id, request.attached_media_urls, request.reply_to_message_id)
    await router.broker.publish(
        topic="chat.dating.message.created",
        message=res.model_dump_json()
    )
    return res

@router.subscriber("chat.group.created", group_id="alert-chat-group-created")
async def alert_chat_group_created(event: ChatCreatedEvent) -> None:
    ws_manager = WebSocketManager()
    await ws_manager.ensure_conversations(event.conversation_id)
    data = {
        "message_type": "alert-chat-group-created",
        "data": event.model_dump(),
    }
    await ws_manager.send_message(json.dumps(data), event.conversation_id, user_id=None, socket_id=None)

@router.subscriber("chat.private.created", group_id="alert-chat-private-created")
async def alert_chat_private_created(event: ChatCreatedEvent) -> None:
    ws_manager = WebSocketManager()
    await ws_manager.ensure_conversations(event.conversation_id)
    data = {
        "message_type": "alert-chat-private-created",
        "data": event.model_dump(),
    }
    await ws_manager.send_message(json.dumps(data), event.conversation_id, user_id=None, socket_id=None)

@router.subscriber("chat.dating.created", group_id="alert-chat-dating-created")
async def alert_chat_dating_created(event: ChatCreatedEvent) -> None:
    ws_manager = WebSocketManager()
    await ws_manager.ensure_conversations(event.conversation_id)
    data = {
        "message_type": "alert-chat-dating-created",
        "data": event.model_dump(),
    }
    await ws_manager.send_message(json.dumps(data), event.conversation_id, user_id=None, socket_id=None)


@router.subscriber("chat.group.message.created", group_id="alert-chat-group-message-created")
async def alert_chat_group_message_created_event(event: ConversationMessageEvent) -> None:
    # Fetch participants
    participants_query = """
    MATCH (u:User)-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    RETURN u.user_id AS user_id
    """
    participants_params = {
        "conversation_id": event.conversation_id,
    }

    async with driver.session() as session:
        participants_result = await session.run(participants_query, participants_params)
        participants = await participants_result.data()
        for participant in participants:
            participant_id = participant["user_id"]
            modified_message = ConversationMessageEvent(**event.model_dump())

            if modified_message.attached_post and not await is_post_accessible_to_user(modified_message.attached_post.post_id, participant_id):
                modified_message = ConversationMessageEvent(
                    conversation_id=event.conversation_id,
                    message_id=modified_message.message_id,
                    content=modified_message.content,
                    created_at=modified_message.created_at,
                    sender=modified_message.sender,
                    attached_post=PostPreview(
                        post_id=modified_message.attached_post.post_id,
                        content_preview="You do not have permission to view this post.",
                        user=None,
                        created_at=modified_message.attached_post.created_at,
                        is_accessible=False
                    ),
                    attached_media_urls=modified_message.attached_media_urls,
                    reply_to=modified_message.reply_to,
                    reactions=modified_message.reactions
                )
            ws_manager = WebSocketManager()
            response_data: dict[str, Any] = {}
            response_data["message_type"] = "alert-chat-group-message-created"
            response_data["data"] = modified_message.model_dump()
            await ws_manager.ensure_conversations(event.conversation_id)
            await ws_manager.send_message(json.dumps(response_data), event.conversation_id)

@router.subscriber("chat.private.message.created", group_id="alert-chat-private-message-created")
async def alert_chat_private_message_created_event(event: ConversationMessageEvent) -> None:
    # Fetch participants
    participants_query = """
    MATCH (u:User)-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    RETURN u.user_id AS user_id
    """
    participants_params = {
        "conversation_id": event.conversation_id,
    }
    async with driver.session() as session:
        participants_result = await session.run(participants_query, participants_params)
        participants = await participants_result.data()
        for participant in participants:
            participant_id = participant["user_id"]
            modified_message = ConversationMessageEvent(**event.model_dump())

            if modified_message.attached_post and not await is_post_accessible_to_user(modified_message.attached_post.post_id, participant_id):
                modified_message = ConversationMessageEvent(
                    conversation_id=event.conversation_id,
                    message_id=modified_message.message_id,
                    content=modified_message.content,
                    created_at=modified_message.created_at,
                    sender=modified_message.sender,
                    attached_post=PostPreview(
                        post_id=modified_message.attached_post.post_id,
                        content_preview="You do not have permission to view this post.",
                        user=None,
                        created_at=modified_message.attached_post.created_at,
                        is_accessible=False
                    ),
                    attached_media_urls=modified_message.attached_media_urls,
                    reply_to=modified_message.reply_to,
                    reactions=modified_message.reactions
                )
            ws_manager = WebSocketManager()
            response_data: dict[str, Any] = {}
            response_data["message_type"] = "alert-chat-private-message-created"
            response_data["data"] = modified_message.model_dump()
            await ws_manager.ensure_conversations(event.conversation_id)
            await ws_manager.send_message(json.dumps(response_data), event.conversation_id)

@router.subscriber("chat.dating.message.created", group_id="alert-chat-dating-message-created")
async def alert_chat_dating_message_created_event(event: ConversationMessageEvent) -> None:
    # Fetch participants
    participants_query = """
    MATCH (u:User)-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    RETURN u.user_id AS user_id
    """
    participants_params = {
        "conversation_id": event.conversation_id,
    }
    async with driver.session() as session:
        participants_result = await session.run(participants_query, participants_params)
        participants = await participants_result.data()
        for participant in participants:
            participant_id = participant["user_id"]
            modified_message = ConversationMessageEvent(**event.model_dump())

            if modified_message.attached_post and not await is_post_accessible_to_user(modified_message.attached_post.post_id, participant_id):
                modified_message = ConversationMessageEvent(
                    conversation_id=event.conversation_id,
                    message_id=modified_message.message_id,
                    content=modified_message.content,
                    created_at=modified_message.created_at,
                    sender=modified_message.sender,
                    attached_post=PostPreview(
                        post_id=modified_message.attached_post.post_id,
                        content_preview="You do not have permission to view this post.",
                        user=None,
                        created_at=modified_message.attached_post.created_at,
                        is_accessible=False
                    ),
                    attached_media_urls=modified_message.attached_media_urls,
                    reply_to=modified_message.reply_to,
                    reactions=modified_message.reactions
                )
            ws_manager = WebSocketManager()
            response_data: dict[str, Any] = {}
            response_data["message_type"] = "alert-chat-dating-message-created"
            response_data["data"] = modified_message.model_dump()
            await ws_manager.ensure_conversations(event.conversation_id)
            await ws_manager.send_message(json.dumps(response_data), event.conversation_id)