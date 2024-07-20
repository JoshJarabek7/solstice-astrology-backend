from faststream.kafka.fastapi import KafkaRouter
from loguru import logger

from app.interactions.schemas import MatchEvent

router = KafkaRouter()

@router.subscriber("dating.match", group_id="notifications-dating-matches")
async def notify_matches_event(event: MatchEvent) -> None:
    