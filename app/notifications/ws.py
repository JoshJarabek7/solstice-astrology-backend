import asyncio
from uuid import uuid4

from fastapi import HTTPException, WebSocket, WebSocketException, status
from loguru import logger

from app.shared.neo4j import driver

"""
Anytime someone sends a message in a conversation, we grab the conversation ID
and query the database for the conversation details, and add the user_ids to the
conversation dictionary.

First, we see if the conversation ID is already in teh active conversations

If it's not, we query the database for the conversation details and add the
user_ids to the conversation dictionary.

User ids won't take up too much space, so we can just keep them in the dictionary as a reference.
"""
class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        self.active_conversations: dict[str, set[str]] = {}
        self.lock = asyncio.Lock()

    async def ensure_conversations(self, conversation_id: str) -> None:
        if conversation_id in self.active_conversations:
            return
        query = """
        MATCH (c:Conversation {conversation_id: $conversation_id})
        MATCH (u:User)-[:PARTICIPATES_IN]->(c)
        RETURN c.conversation_id AS conversation_id, collect(u.user_id) AS participant_ids
        """
        async with driver.session() as session:
            result = await session.run(
                query,
                {
                    "conversation_id": conversation_id,
                },
            )
            record = await result.single()
            if record:
                self.active_conversations[conversation_id] = set(record["participant_ids"])
            else:
                logger.error(f"Failed to find conversation {conversation_id}")
                raise HTTPException(status_code=404, detail="Conversation not found")
        return


    async def user_joined_conversation(self, conversation_id: str, user_id: str) -> None:
        """Adds a user to a conversation.

        We want to only have to query the database once per conversation.
        This will allow us to keep up to date with any new users joining the conversation.
        It will be handled via Kafka subscriptions.

        Args:
            conversation_id (str): The ID of the conversation.
            user_id (str): The ID of the user.

        Returns:
            None
        """
        if conversation_id not in self.active_conversations:
            return
        self.active_conversations[conversation_id].add(user_id)
        return

    async def user_left_conversation(self, conversation_id: str, user_id: str) -> None:
        """Removes a user from a conversation.

        We want to only have to query the database once per conversation.
        This will prevent us from messaging users who have left the conversation.

        Args:
            conversation_id (str): The ID of the conversation.
            user_id (str): The ID of the user.

        Returns:
            None
        """
        if conversation_id not in self.active_conversations:
            return
        self.active_conversations[conversation_id].remove(user_id)
        return


    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Accepts a websocket connection and adds it to the active connections dictionary."""
        await websocket.accept()
        socket_id = str(uuid4())
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}
            self.active_connections[user_id][socket_id] = websocket
        return socket_id

    async def disconnect(self, user_id: str, socket_id: str) -> None:
        """Removes a websocket connection from the active connections dictionary."""
        async with self.lock:
            try:
                if user_id in self.active_connections:
                    if socket_id in self.active_connections[user_id]:
                        websocket = self.active_connections[user_id][socket_id]
                        if websocket:
                            try:
                                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Client disconnected")
                            except WebSocketException as e:
                                logger.error(f"Error in closing websocket: {e}")
                        del self.active_connections[user_id][socket_id]
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]
            except Exception as e:
                logger.error(f"Error in disconnecting websocket: {e}")

    async def broadcast(self, notification: str, user_id: str) -> None:
        """Broadcasts a JSON string to all connected websockets for a given user."""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id].values():
                await websocket.send_json(notification, mode="json")

    async def send_message(self, data: str, conversation_id: str, user_id: str | None = None, socket_id: str | None = None) -> None:
        """Sends a new message to the user's in a conversation.

        The socket ID will allow us to not send the same message to the same user's device twice.

        Args:
            data (str): The JSON string of the message data.
            conversation_id (str): The ID of the conversation.
            user_id (str | None): The ID of the user.
            socket_id (str | None): The socket ID.

        Returns:
            None
        """
        if conversation_id not in self.active_connections:
            return
        if user_id not in self.active_connections[conversation_id]:
            return
        for users in self.active_connections[conversation_id].values():
            for sid, websocket in users.items():
                if not socket_id or sid != socket_id:
                    await websocket.send_json(data, mode="json")

    async def send_to_user(self, notification: str, user_id: str) -> None:
        """Sends a JSON string to a single connected websocket for a given user."""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id].values():
                await websocket.send_json(notification, mode="json")

    async def send_to_socket(self, data: str, user_id: str, socket_id: str) -> None:
        """Sends a JSON string to a single connected websocket."""
        if user_id in self.active_connections:
            for sock in self.active_connections[user_id].values():
                if sock == socket_id:
                    await sock.send_json(data, mode="json")
