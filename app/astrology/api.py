
from fastapi import Depends
from faststream.kafka.fastapi import KafkaRouter

from app.astrology.db import compare_astrology_couple, create_astrology_chart, get_astrology_profile
from app.astrology.schemas import AstrologyChartCreationRequest, AstrologyDetailsCompared, AstrologyDetailsSingleUser
from app.shared.auth import get_current_user
from app.users.schemas import VerifiedUser

router = KafkaRouter()

@router.get("/api/astrology/{user_id}", response_model=AstrologyDetailsSingleUser)
async def get_astrology_profile_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> AstrologyDetailsSingleUser:
    return await get_astrology_profile(verified_user.user_id, user_id)

@router.post("/api/astrology", response_model=None)
async def create_astrology_chart_route(
    request: AstrologyChartCreationRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    await create_astrology_chart(verified_user.user_id, request.birth_datetime, request.latitude, request.longitude)

@router.get("/api/astrology/couple/{user_id}", response_model=AstrologyDetailsCompared)
async def compare_astrology_couple_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> AstrologyDetailsCompared:
    return await compare_astrology_couple(verified_user.user_id, user_id)
