from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.users.schemas import SimpleUserResponse


class PostPreview(BaseModel):
    post_id: str
    content_preview: Optional[str]
    user: Optional[SimpleUserResponse]
    created_at: datetime
    is_accessible: bool

class MessageReaction(BaseModel):
    emoji: str
    reactor_id: str

class MediaAttachment(BaseModel):
    type: Literal['image', 'video']
    url: str

class ConversationMessage(BaseModel):
    message_id: str
    content: str
    created_at: datetime
    sender: SimpleUserResponse
    attached_post: Optional[PostPreview] = None
    attached_media: Optional[MediaAttachment] = None
    reply_to: Optional['ConversationMessage'] = None
    reactions: list[MessageReaction] = []

ConversationMessage.model_rebuild()

class InitialMessage(BaseModel):
    content: str
    attached_post_id: str | None = None
    attached_media_urls: list[str] | None = None

class CreateConversationRequest(BaseModel):
    conversation_type: str
    participants: list[str]
    initial_message: InitialMessage

class ConversationMessageEvent(BaseModel):
    message_id: str
    conversation_id: str
    content: str
    created_at: datetime
    sender_id: str
    attached_post: Optional[PostPreview]
    attached_media: Optional[MediaAttachment]
    reply_to: Optional[ConversationMessage]
    reactions: list[MessageReaction]

class CreateGroupChatRequest(BaseModel):
    participants: list[str] # All users in the group chat
    conversation_type: str = "group"
    initial_message: InitialMessage
    title: str | None = "N/A"
    description: str | None = None

class CreatePrivateChatRequest(BaseModel):
    participants: list[str] # Both users in the single chat
    conversation_type: str = "private"
    initial_message: InitialMessage

class CreateDatingChatRequest(BaseModel):
    participants: list[str] # Both users in the dating match
    conversation_type: str = "dating"
    initial_message: InitialMessage

class ChatCreatedEvent(CreateConversationRequest):
    conversation_id: str
    message_id: str

class MessageReactionEvent(BaseModel):
    """Event for when a user reacts to a message.

    Keeps track of the reactions for the message.
    """
    message_id: str
    user_id: str
    reaction: str # emoji

class ConversationReadEvent(BaseModel):
    """Event for when a user reads a conversation.

    Removes the Unread status from the conversation.
    """
    conversation_id: str
    user_id: str

class ConversationPageVisitedEvent(BaseModel):
    """Event for when a user visits a conversation page.

    To update the user's property for the last time they visited the conversation page,
    so that we can determine whether to show the "New messages" indicator.
    """
    user_id: str