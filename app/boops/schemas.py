from datetime import datetime

from pydantic import BaseModel

from app.users.schemas import SimpleUserResponse


class BoopRequest(BaseModel):
    requesting_user_id: str
    target_user_id: str

class BoopEvent(BaseModel):
    boop_id: str
    total_boops: int
    booper: SimpleUserResponse
    booped_user_id: str
    turn_id: str

class BoopSingle(BaseModel):
    total_boops: int
    booper: SimpleUserResponse
    boop_id: str
    turn_id: str
    created_at: datetime
    updated_at: datetime

class BoopListRequest(BaseModel):
    user_id: str
    exclude_boop_ids: list[str] = []
    limit: int = 10

class BoopListResponse(BaseModel):
    boops: list[BoopSingle]
    has_more: bool