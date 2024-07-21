import json

from fastapi import Depends, HTTPException, status
from faststream.kafka.fastapi import KafkaRouter
from loguru import logger

from app.boops.db import boop_user, get_boop_list
from app.boops.schemas import (BoopEvent, BoopListRequest, BoopListResponse,
                               BoopRequest)
from app.notifications.ws import WebSocketManager
from app.shared.auth import get_current_user
from app.users.schemas import VerifiedUser

router = KafkaRouter()


@router.subscriber("boop.booped", group_id="alert-booped")
async def alert_user_booped_event(event: BoopEvent) -> None:
    logger.info(f"User {event.booper.user_id} booped user {event.booped_user_id}")
    ws_manager = WebSocketManager()
    data = {
        "message_type": "alert-booped",
        "data": {
            "boop_id": event.boop_id,
            "total_boops": event.total_boops,
            "booper": event.booper.model_dump(),
            "booped_user_id": event.booped_user_id,
            "turn_id": event.turn_id,
        }
    }
    await ws_manager.send_to_user(json.dumps(data), event.booped_user_id)

@router.post("/api/boop/list", response_model=BoopListResponse)
async def get_boop_list_route(request: BoopListRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> BoopListResponse:
    return await get_boop_list(request)


@router.post("/api/boop", response_model=None)
async def boop_user_route(request: BoopRequest, verified_user: VerifiedUser = Depends(get_current_user)) -> None:
    logger.info(f"Received boop request for user {request.requesting_user_id} to boop user {request.target_user_id}")
    if not request.requesting_user_id == verified_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )
    res = await boop_user(request)
    logger.info(f"Booped user {request.target_user_id} for user {request.requesting_user_id}")
    await router.broker.publish(
        topic="boop.booped",
        message=res.model_dump_json(),
    )
