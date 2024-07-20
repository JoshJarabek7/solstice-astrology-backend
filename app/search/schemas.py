from pydantic import BaseModel

from app.users.schemas import SimpleUserResponse


class SearchUserResponse(BaseModel):
    users: list[SimpleUserResponse]