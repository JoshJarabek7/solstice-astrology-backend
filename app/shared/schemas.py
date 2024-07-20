from pydantic import BaseModel


class WasSuccessfulResponse(BaseModel):
    """Response model for basic success."""

    successful: bool
