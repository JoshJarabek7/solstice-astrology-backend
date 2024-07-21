from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.chat.schemas import (ConversationMessage, ConversationMessageEvent,
                              CreateDatingChatRequest, CreateGroupChatRequest,
                              CreatePrivateChatRequest, MessageReaction,
                              PostPreview)
from app.shared.neo4j import driver
from app.users.schemas import SimpleUserResponse


async def get_attached_post(post_id: str, user_id: str) -> PostPreview | None:
    query = """
    MATCH (post:Post {post_id: $post_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    OPTIONAL MATCH (user:User {user_id: $user_id})
    WHERE NOT (author)-[:BLOCKS]-(user) AND (NOT author.account_private OR (user)-[:FOLLOWS]->(author))
    RETURN post {
        .post_id,
        .content,
        .created_at
    } AS post,
    author {
        .user_id,
        .username,
        .display_name,
        .profile_photo
    } AS user,
    CASE
        WHEN author IS NULL THEN false
        WHEN NOT (author)-[:BLOCKS]-(user) AND (NOT author.account_private OR (user)-[:FOLLOWS]->(author)) THEN true
        ELSE false
    END AS is_accessible
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "user_id": user_id,
            }
        )
        record = await result.single()

        if record and record["post"]:
            return PostPreview(
                post_id=record["post"]["post_id"],
                content_preview=record["post"]["content"][:100] if record["is_accessible"] else None,
                user=SimpleUserResponse(**record["user"]) if record["user"] and record["is_accessible"] else None,
                created_at=record["post"]["created_at"],
                is_accessible=record["is_accessible"]
            )
        return None

async def get_replied_to_message(message_id: str, user_id: str) -> ConversationMessage | None:
    query = """
    MATCH (u:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation)-[:REPLIED_TO]->(m:Message {message_id: $message_id})
    MATCH (m)-[:IN]->(c)
    MATCH (sender:User)-[:SENT]->(m)
    RETURN m {
        .message_id,
        .content,
        .created_at,
        sender {
            .user_id,
            .username,
            .display_name,
            .profile_photo
        }
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "message_id": message_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Message not found.")
        return ConversationMessage(
            message_id=record["message_id"],
            content=record["content"],
            created_at=datetime.fromisoformat(record["created_at"]),
            sender=SimpleUserResponse(**record["sender"]),
            attached_post=None,
            attached_media_urls=None,
            reply_to=None,
            reactions=[],
        )

async def get_conversation_messages(conversation_id: str, user_id: str, cursor: str | None = None, limit: int = 20):
    query = """
    MATCH (u:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    MATCH (m:Message)-[:IN]->(c)
    WHERE m.created_at < $cursor
    WITH m
    ORDER BY m.created_at DESC
    LIMIT $limit

    MATCH (sender:User)-[:SENT]->(m)
    OPTIONAL MATCH (m)-[:ATTACHED_TO_POST]->(p:Post)<-[:POSTED]-(post_author:User)
    OPTIONAL MATCH (m)-[:REPLY_TO_MESSAGE]->(reply:Message)<-[:SENT]-(reply_sender:User)
    OPTIONAL MATCH (u)-[:FOLLOWS]->(post_author)
    OPTIONAL MATCH (u)-[:BLOCKS]-(post_author)
    OPTIONAL MATCH (m)<-[r:REACTED]-(reactor:User)

    WITH m, sender, p, post_author, reply, reply_sender, u,
         CASE WHEN p IS NOT NULL
              THEN CASE WHEN post_author.account_private AND NOT (u)-[:FOLLOWS]->(post_author) THEN false
                        WHEN (u)-[:BLOCKS]-(post_author) THEN false
                        ELSE true
                   END
              ELSE null
         END AS is_post_accessible,
         collect(DISTINCT {emoji: r.emoji, reactor_id: reactor.user_id}) AS reactions

    RETURN m.message_id AS message_id,
           m.content AS content,
           m.created_at AS created_at,
           m.media_attachment_type AS media_attachment_type,
           m.attached_media_url AS attached_media_url,
           sender {.user_id, .username, .display_name, .profile_photo} AS sender,
           CASE WHEN p IS NOT NULL
                THEN {
                    post_id: p.post_id,
                    content_preview: CASE WHEN is_post_accessible THEN left(p.content, 100) ELSE null END,
                    user: CASE WHEN is_post_accessible THEN post_author {.user_id, .username, .display_name, .profile_photo} ELSE null END,
                    created_at: p.created_at,
                    is_accessible: is_post_accessible
                }
                ELSE null
           END AS attached_post,
           CASE WHEN reply IS NOT NULL
                THEN {
                    message_id: reply.message_id,
                    content: reply.content,
                    created_at: reply.created_at,
                    sender: reply_sender {.user_id, .username, .display_name, .profile_photo}
                }
                ELSE null
           END AS reply_to,
           reactions
    ORDER BY m.created_at DESC
    """

    params = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "cursor": cursor or datetime.now().isoformat(),
        "limit": limit + 1,  # Fetch one extra to check if there are more messages
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        records = await result.data()

    messages: list[ConversationMessage] = []
    for record in records:
        attached_post = None
        if record["attached_post"]:
            attached_post = PostPreview(
                post_id=record["attached_post"]["post_id"],
                content_preview=record["attached_post"]["content_preview"],
                user=SimpleUserResponse(**record["attached_post"]["user"]) if record["attached_post"]["user"] else None,
                created_at=record["attached_post"]["created_at"],
                is_accessible=record["attached_post"]["is_accessible"],
            )

        attached_media_urls = None
        if record["media_attachment_type"] and record["attached_media_url"]:
            attached_media_urls = [record["attached_media_url"]]

        reply_to = None
        if record["reply_to"]:
            reply_to = ConversationMessage(
                message_id=record["reply_to"]["message_id"],
                content=record["reply_to"]["content"],
                created_at=record["reply_to"]["created_at"],
                sender=SimpleUserResponse(**record["reply_to"]["sender"]),
                attached_post=None,
                attached_media_urls=None,
                reply_to=None,
                reactions=[],
            )

        message: ConversationMessage = ConversationMessage(
            message_id=record["message_id"],
            content=record["content"],
            created_at=record["created_at"],
            sender=SimpleUserResponse(**record["sender"]),
            attached_post=attached_post,
            attached_media_urls=attached_media_urls,
            reply_to=reply_to,
            reactions=[MessageReaction(**r) for r in record["reactions"]],
        )
        messages.append(message)

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    return {
        "messages": messages,
        "has_more": has_more,
        "next_cursor": messages[-1].created_at.isoformat() if has_more else None,
    }

async def create_group_chat(request: CreateGroupChatRequest, sender_id: str):
    query = """
    // Ensure there are at least 3 participants (including sender)
    WITH $participants + [$sender_id] AS all_participants
    WHERE size(all_participants) >= 3

    // Check for blocking relationships
    MATCH (sender:User {user_id: $sender_id})
    UNWIND $participants AS participant_id
    MATCH (participant:User {user_id: participant_id})
    WHERE NOT (sender)-[:BLOCKS]-(participant)
    WITH collect(participant_id) + [$sender_id] AS allowed_participants, sender

    // Create the group chat
    CREATE (c:Conversation:GroupChat {
        conversation_id: $conversation_id,
        conversation_type: 'group',
        created_at: $created_at,
        title: $title,
        description: $description
    })

    // Add participants
    WITH c, allowed_participants, sender
    UNWIND allowed_participants AS participant_id
    MATCH (u:User {user_id: participant_id})
    CREATE (u)-[:PARTICIPATES_IN]->(c)

    // Create the initial message
    CREATE (m:Message {
        message_id: $message_id,
        content: $initial_message.content,
        created_at: $created_at
    })
    CREATE (m)-[:IN]->(c)
    CREATE (sender)-[:SENT]->(m)

    // Handle attached post if present
    FOREACH (post_id IN CASE WHEN $initial_message.attached_post_id IS NOT NULL
                              THEN [$initial_message.attached_post_id] ELSE [] END |
        MATCH (p:Post {post_id: post_id})
        CREATE (m)-[:ATTACHED_TO_POST]->(p)
    )

    // Handle attached media if present
    FOREACH (media_url IN $initial_message.attached_media_urls |
        CREATE (m)-[:HAS_MEDIA]->(:Media {url: media_url})
    )

    RETURN c.conversation_id AS conversation_id, m.message_id AS message_id
    """

    params = {
        "participants": request.participants,
        "sender_id": sender_id,
        "title": request.title,
        "description": request.description,
        "initial_message": request.initial_message.model_dump(),
        "conversation_id": str(uuid4()),
        "message_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"],
        }
    else:
        raise ValueError("Failed to create group chat. Ensure there are at least 3 participants and no blocking relationships.")

async def create_private_chat(request: CreatePrivateChatRequest, sender_id: str):
    query = """
    // Ensure there are exactly 2 participants (including sender)
    WITH $participants + [$sender_id] AS all_participants
    WHERE size(all_participants) = 2

    // Check for blocking relationships
    MATCH (sender:User {user_id: $sender_id})
    UNWIND $participants AS participant_id
    MATCH (participant:User {user_id: participant_id})
    WHERE NOT (sender)-[:BLOCKS]-(participant)
    WITH collect(participant_id) + [$sender_id] AS allowed_participants, sender

    // Check for existing conversation
    OPTIONAL MATCH (sender)-[:PARTICIPATES_IN]->(existing:Conversation:PrivateChat)<-[:PARTICIPATES_IN]-(other:User)
    WHERE other.user_id IN allowed_participants AND other.user_id <> sender.user_id

    // Create new conversation if it doesn't exist
    FOREACH (x IN CASE WHEN existing IS NULL THEN [1] ELSE [] END |
        CREATE (c:Conversation:PrivateChat {
            conversation_id: $conversation_id,
            conversation_type: 'private',
            created_at: $created_at
        })
        WITH c, allowed_participants
        UNWIND allowed_participants AS participant_id
        MATCH (u:User {user_id: participant_id})
        CREATE (u)-[:PARTICIPATES_IN]->(c)
        SET existing = c
    )

    // Use the existing or newly created conversation
    WITH coalesce(existing, c) AS conversation, sender

    // Create the initial message
    CREATE (m:Message {
        message_id: $message_id,
        content: $initial_message.content,
        created_at: $created_at
    })
    CREATE (m)-[:IN]->(conversation)
    CREATE (sender)-[:SENT]->(m)

    // Handle attached post if present
    FOREACH (post_id IN CASE WHEN $initial_message.attached_post_id IS NOT NULL
                              THEN [$initial_message.attached_post_id] ELSE [] END |
        MATCH (p:Post {post_id: post_id})
        CREATE (m)-[:ATTACHED_TO_POST]->(p)
    )

    // Handle attached media if present
    FOREACH (media_url IN $initial_message.attached_media_urls |
        CREATE (m)-[:HAS_MEDIA]->(:Media {url: media_url})
    )

    RETURN conversation.conversation_id AS conversation_id, m.message_id AS message_id
    """

    params = {
        "participants": request.participants,
        "sender_id": sender_id,
        "initial_message": request.initial_message.model_dump(),
        "conversation_id": str(uuid4()),
        "message_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"],
        }
    else:
        raise ValueError("Failed to create private chat. Ensure there are exactly 2 participants and no blocking relationships.")


async def create_dating_chat(request: CreateDatingChatRequest, sender_id: str):
    query = """
    // Ensure there are exactly 2 participants (including sender)
    WITH $participants + [$sender_id] AS all_participants
    WHERE size(all_participants) = 2

    // Check for blocking relationships
    MATCH (sender:User {user_id: $sender_id})
    UNWIND $participants AS participant_id
    MATCH (participant:User {user_id: participant_id})
    WHERE NOT (sender)-[:BLOCKS]-(participant)
    WITH collect(participant_id) + [$sender_id] AS allowed_participants, sender

    // Check for existing dating conversation
    OPTIONAL MATCH (sender)-[:PARTICIPATES_IN]->(existing:Conversation:DatingChat)<-[:PARTICIPATES_IN]-(other:User)
    WHERE other.user_id IN allowed_participants AND other.user_id <> sender.user_id

    // Create new conversation if it doesn't exist
    FOREACH (x IN CASE WHEN existing IS NULL THEN [1] ELSE [] END |
        CREATE (c:Conversation:DatingChat {
            conversation_id: $conversation_id,
            conversation_type: 'dating',
            created_at: $created_at
        })
        WITH c, allowed_participants
        UNWIND allowed_participants AS participant_id
        MATCH (u:User {user_id: participant_id})
        CREATE (u)-[:PARTICIPATES_IN]->(c)
        SET existing = c
    )

    // Use the existing or newly created conversation
    WITH coalesce(existing, c) AS conversation, sender

    // Create the initial message
    CREATE (m:Message {
        message_id: $message_id,
        content: $initial_message.content,
        created_at: $created_at
    })
    CREATE (m)-[:IN]->(conversation)
    CREATE (sender)-[:SENT]->(m)

    // Handle attached post if present
    FOREACH (post_id IN CASE WHEN $initial_message.attached_post_id IS NOT NULL
                              THEN [$initial_message.attached_post_id] ELSE [] END |
        MATCH (p:Post {post_id: post_id})
        CREATE (m)-[:ATTACHED_TO_POST]->(p)
    )

    // Handle attached media if present
    FOREACH (media_url IN $initial_message.attached_media_urls |
        CREATE (m)-[:HAS_MEDIA]->(:Media {url: media_url})
    )

    RETURN conversation.conversation_id AS conversation_id, m.message_id AS message_id
    """

    params = {
        "participants": request.participants,
        "sender_id": sender_id,
        "initial_message": request.initial_message.model_dump(),
        "conversation_id": str(uuid4()),
        "message_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"],
        }
    else:
        raise ValueError("Failed to create dating chat. Ensure there are exactly 2 participants and no blocking relationships.")


from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.chat.schemas import (ConversationMessage, CreateDatingChatRequest,
                              CreateGroupChatRequest, CreatePrivateChatRequest,
                              MessageReaction, PostPreview)
from app.shared.neo4j import driver
from app.users.schemas import SimpleUserResponse


async def create_group_chat_message(conversation_id: str, sender_id: str, content: str, attached_post_id: str | None = None, attached_media_urls: list[str] = [], reply_to_message_id: str | None = None) -> ConversationMessageEvent:
    query = """
    MATCH (sender:User {user_id: $sender_id})-[:PARTICIPATES_IN]->(c:Conversation:GroupChat {conversation_id: $conversation_id})
    WHERE c.conversation_type = 'group'
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        attached_media: $attached_media,
        attached_post_id: $attached_post_id,
        reply_to_message_id: $reply_to_message_id,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(m)-[:IN]->(c)

    WITH m, c, sender

    OPTIONAL MATCH (reply_to:Message {message_id: m.reply_to_message_id})-[:IN]->(c)
    OPTIONAL MATCH (reply_to)<-[:SENT]-(reply_sender:User)

    WITH m, c, sender, reply_to, reply_sender

    MATCH (participant:User)-[:PARTICIPATES_IN]->(c)
    WHERE participant.user_id <> $sender_id
    CREATE (participant)-[:UNREAD]->(m)

    RETURN m {
        .message_id,
        .content,
        .attached_media,
        .attached_post_id,
        .reply_to_message_id,
        .created_at
    } AS message,
    sender {
        .user_id,
        .username,
        .display_name,
        .profile_photo
    } AS sender,
    CASE WHEN reply_to IS NOT NULL
        THEN reply_to {
            .message_id,
            .content,
            .created_at,
            sender: reply_sender {
                .user_id,
                .username,
                .display_name,
                .profile_photo
            }
        }
        ELSE null
    END AS reply_to
    """

    params = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message_id": str(uuid4()),
        "content": content,
        "attached_media": attached_media_urls,
        "attached_post_id": attached_post_id,
        "reply_to_message_id": reply_to_message_id,
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Conversation not found or user is not a participant")

        message_data = record["message"]
        sender_data = record["sender"]
        reply_to_data = record["reply_to"]

        reply_to = None
        if reply_to_data:
            reply_to = ConversationMessage(
                message_id=reply_to_data["message_id"],
                content=reply_to_data["content"],
                created_at=reply_to_data["created_at"],
                sender=SimpleUserResponse(**reply_to_data["sender"]),
                attached_post=None,  # We're not fetching this information for the replied message
                attached_media_urls=None,  # We're not fetching this information for the replied message
                reply_to=None,
                reactions=[]
            )

        message = ConversationMessage(
            message_id=message_data["message_id"],
            content=message_data["content"],
            created_at=message_data["created_at"],
            sender=SimpleUserResponse(**sender_data),
            attached_post=None,  # This needs to be fetched separately if needed
            attached_media_urls=[url for url in message_data["attached_media"]] if message_data["attached_media"] else None,
            reply_to=reply_to,
            reactions=[]
        )

        if message_data["attached_post_id"]:
            attached_post = await get_attached_post(message_data["attached_post_id"], sender_id)
            message.attached_post = attached_post
        res = message.model_dump()
        res["conversation_id"] = conversation_id
        return ConversationMessageEvent(**res)

async def create_private_chat_message(conversation_id: str, sender_id: str, content: str, attached_post_id: str | None = None, attached_media_urls: list[str] = [], reply_to_message_id: str | None = None) -> ConversationMessageEvent:
    query = """
    MATCH (sender:User {user_id: $sender_id})-[:PARTICIPATES_IN]->(c:Conversation:PrivateChat {conversation_id: $conversation_id})
    WHERE c.conversation_type = 'private'
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        attached_media: $attached_media,
        attached_post_id: $attached_post_id,
        reply_to_message_id: $reply_to_message_id,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(m)-[:IN]->(c)
    WITH m, c, sender
    OPTIONAL MATCH (reply_to:Message {message_id: m.reply_to_message_id})-[:IN]->(c)
    OPTIONAL MATCH (reply_to)<-[:SENT]-(reply_sender:User)
    WITH m, c, sender, reply_to, reply_sender
    MATCH (participant:User)-[:PARTICIPATES_IN]->(c)
    WHERE participant.user_id <> $sender_id
    CREATE (participant)-[:UNREAD]->(m)

    RETURN m {
        .message_id,
        .content,
        .attached_media,
        .attached_post_id,
        .reply_to_message_id,
        .created_at
        } AS message,
        sender {
        .user_id,
        .username,
        .display_name,
        .profile_photo
        } AS sender,
        CASE WHEN reply_to IS NOT NULL
            THEN reply_to {
            .message_id,
            .content,
            .created_at,
            sender: reply_sender {
                .user_id,
                .username,
                .display_name,
                .profile_photo
            }
        }
        ELSE null
    END AS reply_to
    """
    params = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message_id": str(uuid4()),
        "content": content,
        "attached_media": attached_media_urls,
        "attached_post_id": attached_post_id,
        "reply_to_message_id": reply_to_message_id,
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Conversation not found or user is not a participant")
        message_data = record["message"]
        sender_data = record["sender"]
        reply_to_data = record["reply_to"]

        reply_to = None
        if reply_to_data:
            reply_to = ConversationMessage(
                message_id=reply_to_data["message_id"],
                content=reply_to_data["content"],
                created_at=reply_to_data["created_at"],
                sender=SimpleUserResponse(**reply_to_data["sender"]),
                attached_post=None,  # We're not fetching this information for the replied message
                attached_media_urls=None,  # We're not fetching this information for the replied message
                reply_to=None,
                reactions=[]
            )
        message = ConversationMessage(
            message_id=message_data["message_id"],
            content=message_data["content"],
            created_at=message_data["created_at"],
            sender=SimpleUserResponse(**sender_data),
            attached_post=None,  # This needs to be fetched separately if needed
            attached_media_urls=[url for url in message_data["attached_media"]] if message_data["attached_media"] else None,
            reply_to=reply_to,
            reactions=[]
        )

        if message_data["attached_post_id"]:
            attached_post = await get_attached_post(message_data["attached_post_id"], sender_id)
            message.attached_post = attached_post
        res = message.model_dump()
        res["conversation_id"] = conversation_id
        return ConversationMessageEvent(**res)

async def create_dating_chat_message(conversation_id: str, sender_id: str, content: str, attached_post_id: str | None = None, attached_media_urls: list[str] = [], reply_to_message_id: str | None = None) -> ConversationMessageEvent:
    query = """
    MATCH (sender:User {user_id: $sender_id})-[:PARTICIPATES_IN]->(c:Conversation:DatingChat {conversation_id: $conversation_id})
    WHERE c.conversation_type = 'dating'
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        attached_media: $attached_media,
        attached_post_id: $attached_post_id,
        reply_to_message_id: $reply_to_message_id,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(m)-[:IN]->(c)
    WITH m, c, sender
    OPTIONAL MATCH (reply_to:Message {message_id: m.reply_to_message_id})-[:IN]->(c)
    OPTIONAL MATCH (reply_to)<-[:SENT]-(reply_sender:User)
    WITH m, c, sender, reply_to, reply_sender
    MATCH (participant:User)-[:PARTICIPATES_IN]->(c)
    WHERE participant.user_id <> $sender_id
    CREATE (participant)-[:UNREAD]->(m)
    RETURN m {
        .message_id,
        .content,
        .attached_media,
        .attached_post_id,
        .reply_to_message_id,
        .created_at
        } AS message,
        sender {
        .user_id,
        .username,
        .display_name,
        .profile_photo
        } AS sender,
        CASE WHEN reply_to IS NOT NULL
            THEN reply_to {
            .message_id,
            .content,
            .created_at,
            sender: reply_sender {
                .user_id,
                .username,
                .display_name,
                .profile_photo
            }
        }
        ELSE null
    END AS reply_to
    """
    params = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "message_id": str(uuid4()),
        "content": content,
        "attached_media": attached_media_urls,
        "attached_post_id": attached_post_id,
        "reply_to_message_id": reply_to_message_id,
        "created_at": datetime.now(UTC).isoformat(),
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Conversation not found or user is not a participant")
        message_data = record["message"]
        sender_data = record["sender"]
        reply_to_data = record["reply_to"]

        reply_to = None
        if reply_to_data:
            reply_to = ConversationMessage(
                message_id=reply_to_data["message_id"],
                content=reply_to_data["content"],
                created_at=reply_to_data["created_at"],
                sender=SimpleUserResponse(**reply_to_data["sender"]),
                attached_post=None,  # We're not fetching this information for the replied message
                attached_media_urls=None,  # We're not fetching this information for the replied message
                reply_to=None,
                reactions=[]
            )
        message = ConversationMessage(
            message_id=message_data["message_id"],
            content=message_data["content"],
            created_at=message_data["created_at"],
            sender=SimpleUserResponse(**sender_data),
            attached_post=None,  # This needs to be fetched separately if needed
            attached_media_urls=[url for url in message_data["attached_media"]] if message_data["attached_media"] else None,
            reply_to=reply_to,
            reactions=[]
        )

        if message_data["attached_post_id"]:
            attached_post = await get_attached_post(message_data["attached_post_id"], sender_id)
            message.attached_post = attached_post
        res = message.model_dump()
        res["conversation_id"] = conversation_id
        return ConversationMessageEvent(**res)

async def is_post_accessible_to_user(post_id: str, user_id: str) -> bool:
    query = """
    MATCH (post:Post {post_id: $post_id})<-[:POSTED]-(author:User)
    OPTIONAL MATCH (user:User {user_id: $user_id})
    WHERE NOT (author)-[:BLOCKS]-(user) AND (NOT author.account_private OR (user)-[:FOLLOWS]->(author))
    RETURN CASE
        WHEN author IS NULL THEN false
        WHEN NOT (author)-[:BLOCKS]-(user) AND (NOT author.account_private OR (user)-[:FOLLOWS]->(author)) THEN true
        ELSE false
    END AS is_accessible
    """
    async with driver.session() as session:
        result = await session.run(query, {"post_id": post_id, "user_id": user_id})
        record = await result.single()
        return record["is_accessible"] if record else False