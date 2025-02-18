from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.users.schemas import SimpleUserResponse


class PostPreview(BaseModel):
    post_id: str
    content_preview: str | None
    user: SimpleUserResponse | None
    created_at: datetime
    is_accessible: bool | None = True

class MessageReaction(BaseModel):
    emoji: str
    reactor_id: str

class SendMessageRequest(BaseModel):
    conversation_id: str
    sender_id: str
    content: str
    attached_post_id: str | None = None
    attached_media_urls: list[str] = []
    reply_to_message_id: str | None = None


class ConversationMessage(BaseModel):
    message_id: str
    content: str
    created_at: datetime
    sender: SimpleUserResponse
    attached_post: PostPreview | None = None
    attached_media_urls: list[str] | None = None
    reply_to: Optional["ConversationMessage"] = None
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

class ConversationMessageEvent(ConversationMessage):
    conversation_id: str

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
