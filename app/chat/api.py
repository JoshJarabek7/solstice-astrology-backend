import json

from fastapi import Depends
from faststream.kafka.fastapi import KafkaRouter

from app.chat.db import create_dating_chat, create_group_chat, create_private_chat
from app.chat.schemas import ChatCreatedEvent, CreateDatingChatRequest, CreateGroupChatRequest, CreatePrivateChatRequest
from app.notifications.ws import WebSocketManager
from app.shared.auth import get_current_user
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
