from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from app.chat.schemas import (ConversationMessage, CreateDatingChatRequest,
                              CreateGroupChatRequest, CreatePrivateChatRequest,
                              InitialMessage, MediaAttachment, MessageReaction,
                              PostPreview)
from app.shared.neo4j import driver
from app.users.schemas import SimpleUserResponse


async def get_conversation_messages(conversation_id: str, user_id: str, cursor: Optional[str] = None, limit: int = 20):
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
        "limit": limit + 1  # Fetch one extra to check if there are more messages
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        records = await result.data()

    messages: list[ConversationMessage] = []
    for record in records:
        attached_post = None
        if record['attached_post']:
            attached_post = PostPreview(
                post_id=record['attached_post']['post_id'],
                content_preview=record['attached_post']['content_preview'],
                user=SimpleUserResponse(**record['attached_post']['user']) if record['attached_post']['user'] else None,
                created_at=record['attached_post']['created_at'],
                is_accessible=record['attached_post']['is_accessible']
            )

        attached_media = None
        if record['media_attachment_type'] and record['attached_media_url']:
            attached_media = MediaAttachment(
                type=record['media_attachment_type'],
                url=record['attached_media_url']
            )

        reply_to = None
        if record['reply_to']:
            reply_to = ConversationMessage(
                message_id=record['reply_to']['message_id'],
                content=record['reply_to']['content'],
                created_at=record['reply_to']['created_at'],
                sender=SimpleUserResponse(**record['reply_to']['sender']),
                attached_post=None,
                attached_media=None,
                reply_to=None,
                reactions=[]
            )

        message: ConversationMessage = ConversationMessage(
            message_id=record['message_id'],
            content=record['content'],
            created_at=record['created_at'],
            sender=SimpleUserResponse(**record['sender']),
            attached_post=attached_post,
            attached_media=attached_media,
            reply_to=reply_to,
            reactions=[MessageReaction(**r) for r in record['reactions']]
        )
        messages.append(message)

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    return {
        "messages": messages,
        "has_more": has_more,
        "next_cursor": messages[-1].created_at.isoformat() if has_more else None
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
        "created_at": datetime.now(UTC).isoformat()
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"]
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
        "created_at": datetime.now(UTC).isoformat()
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"]
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
        "created_at": datetime.now(UTC).isoformat()
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()

    if record:
        return {
            "conversation_id": record["conversation_id"],
            "message_id": record["message_id"]
        }
    else:
        raise ValueError("Failed to create dating chat. Ensure there are exactly 2 participants and no blocking relationships.")