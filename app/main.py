"""Main file for the new backend.

TODO: AI to determine what a user looks like and use it to determine a dating taste
    recommendation property

TODO: Poaster of the month
    - At the end of each month, the user that gained the highest score gets a
        bunch of points and is visible on the leaderboards

TODO: Different recommendation engines based on user preferences
    - If they're in a relationship, don't recommend people they might be interested in

TODO: Personality assessment for people who are dating
    - Pass their personality traits to an LLM and have it output suggestions
        - Date ideas
        - Potential land mines to avoid
        - How to love each other better
TODO: Integrate an in-game currency system.
    - Potential names: 'Stardust', 'Loot', 'Points', 'Coins', 'Gold', 'Gems'
    - Keep track of how much they've had in total and how much they've spent in total
    - Subtract the total amount from the total spent to determine their balance
    - Ideas for spending currency:
        - Reveal people who have swiped right on the user's profile
        - Boost their posts
        - Reduce/remove ads
        - In-game when the game has been built
        - Wager on predictions

TODO: Discussions / Roadmap / Ideas / Bug reports
    - Discussion section on the app
        - People can give ideas, ask questions, and report bugs
        - People can also upvote ideas and bugs
        - Rankings for ideas and bugs
        - A way to mark ideas and bugs as fixed / implemented
        - User should get points if their idea gets implemented
        - Use cosine similarity to determine if two ideas or bug reports are too similar

TODO: Integrate a betting system for predictions, where you can wager in-game currency \
    on predictions.
    - Need to create a bookie system for wagers
    - Payouts when a prediction ends
    - Duration remaining of the prediction multiplier

TODO: Attach the SAS token to any media attachments in posts.
    - Determine whether or not we want to have users upload to the server
        or upload to the blob directly from the client
    - Integrate Clip to get tags about the images

TODO: TikTok backend
    - Create a TikTok style backend
    - Public Sounds to add to the video
    - It should have lots of metadata:
        - Tags
        - Description
        - Location
        - Date
        - List of audio used
            - Start time
            - End time
            - Public or Apple Music
            - URL
        - List of text overlays
            - Text
            - Size
            - Rotation
            - Font
            - Color
            - Start time
            - End time
        - Users tagged in the video
        - Transcription
            - Whisper endpoint
        - Extract text from the video
            - OCR like Tesseract
            - Do prior to adding the text overlays
            - Put it in a hash set so there's no duplicates
        - Height
        - Width
        - Embedding
            - Concatenate the text overlays, the tags, the description, captions,
                users tagged in the video, hashtags, transcription, location, date, and
                OCR text, etc.
            - K-means clustering of the embedding
    - Company logo overlays like the one in TikTok
        - Make sure the logo is not too big, moves around, and is behind the text
            overlays

TODO: Meme studio backend
    - Create a meme model
    - Create a Know Your Meme style page for each meme
    - Know Your Meme can be wikipedia-style
    - Have Meme Templates
    - Reusable and public stickers
    - Stickers should have tags and a description
    - Be able to 'see more memes like this'
    - Integrate meme taste into the recommendation engine
    - Meme collection
        - Allow users to store memes on their profile,
            rather than on their device so that they can view
            their memes all in one place
        - Allow users to upload memes to their profile,
            without necessarily create a post for it.

TODO: Change organizations to groups.
    - Check if the user is a member of the group
    - Integrate group membership into recommendations
    - Check if the group name already exists
    - Group location
    - Whether or not it's affiliated with a school
"""

import asyncio
import json
import os
import re
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, LiteralString, Optional, TypeVar, cast
from uuid import UUID, uuid4

import httpx
import jwt
import pytz
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, Query, Security, WebSocket, WebSocketException, status
from fastapi.security import OAuth2PasswordBearer
from faststream.kafka.fastapi import KafkaRouter
from jwt.algorithms import RSAAlgorithm
from loguru import logger
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, EmailStr
from swisseph import (
    FLG_SPEED,
    FLG_SWIEPH,
    JUPITER,
    MARS,
    MERCURY,
    MOON,
    NEPTUNE,
    PLUTO,
    SATURN,
    SE_GREG_CAL,
    SUN,
    URANUS,
    VENUS,
    calc,
    houses,
    julday,
)
from timezonefinder import TimezoneFinder

router = KafkaRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
algorithm = "ES256"
APP_ENV = os.getenv("APP_ENV", "")

"--------------- USER ACCOUNT RELATED FUNCTIONS ---------------"
apple_key_id = os.getenv("APPLE_KEY_ID", "")
apple_developer_team_id = os.getenv("APPLE_DEVELOPER_TEAM_ID", "")
apple_client_id = os.getenv("APPLE_CLIENT_ID", "")
apple_client_secret = os.getenv("APPLE_CLIENT_SECRET", "")
apple_private_key = os.getenv("APPLE_PRIVATE_KEY", "")
apple_auth_token_url = "https://appleid.apple.com/auth/token"  # noqa: S105
apple_auth_keys_url = "https://appleid.apple.com/auth/keys"
apple_issuer = "https://appleid.apple.com"
apple_authorization_url = "https://appleid.apple.com/auth/authorize"

kafka_connection_string = os.getenv("KAFKA_CONNECTION_STRING", "")

azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
azure_openai_embedding_deployment_name = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME",
    "",
)
azure_openai_embedding_dimensions = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DIMENSIONS",
    "256",
)
azure_openai_embedding_api_version = os.getenv(
    "AZURE_OPENAI_EMBEDDING_API_VERSION",
    "",
)
azure_openai_embedding_encoding_format = os.getenv(
    "AZURE_OPENAI_EMBEDDING_ENCODING_FORMAT",
    "float",
)
azure_openai_embedding_model = os.getenv(
    "AZURE_OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-large",
)
azure_openai_embedding_resource = os.getenv("AZURE_EMBEDDING_RESOURCE_NAME", "")

azure_storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
azure_storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
azure_storage_url = os.getenv("AZURE_STORAGE_URL", "")
azure_storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")

neo4j_uri = os.getenv("NEO4J_URI", "")
neo4j_username = os.getenv("NEO4J_USERNAME", "")
neo4j_password = os.getenv("NEO4J_PASSWORD", "")
neo4j_database = os.getenv("NEO4J_DATABASE", "")

jwt_private_key = os.getenv("JWT_PRIVATE_KEY", "")


settings = {
    "apple": {
        "key_id": os.getenv("APPLE_KEY_ID", ""),
        "team_id": os.getenv("APPLE_DEVELOPER_TEAM_ID", ""),
        "client_id": os.getenv("APPLE_CLIENT_ID", ""),
        "client_secret": os.getenv("APPLE_CLIENT_SECRET", ""),
        "private_key": os.getenv("APPLE_PRIVATE_KEY", ""),
        "auth_token_url": "https://appleid.apple.com/auth/token",
        "auth_keys_url": "https://appleid.apple.com/auth/keys",
        "issuer": "https://appleid.apple.com",
        "authorization_url": "https://appleid.apple.com/auth/authorize",
    },
    "kafka": {
        "connection_string": os.getenv("KAFKA_CONNECTION_STRING", ""),
    },
    "azure": {
        "storage": {
            "account_key": os.getenv("AZURE_STORAGE_ACCOUNT_KEY", ""),
            "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
            "url": os.getenv("AZURE_STORAGE_URL", ""),
            "name": os.getenv("AZURE_STORAGE_ACCOUNT_NAME", ""),
        },
        "openai": {
            "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "embedding": {
                "deployment_name": os.getenv(
                    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME",
                    "",
                ),
                "dimensions": int(
                    os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "256"),
                ),
                "version": os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", ""),
                "encoding_format": os.getenv(
                    "AZURE_OPENAI_EMBEDDING_ENCODING_FORMAT",
                    "float",
                ),
                "model": os.getenv(
                    "AZURE_OPENAI_EMBEDDING_MODEL",
                    "text-embedding-3-large",
                ),
                "resource": os.getenv("AZURE_OPENAI_EMBEDDING_RESOURCE", ""),
            },
        },
    },
    "neo4j": {
        "uri": os.getenv("NEO4J_URI", ""),
        "username": os.getenv("NEO4J_USERNAME", ""),
        "password": os.getenv("NEO4J_PASSWORD", ""),
        "database": os.getenv("NEO4J_DATABASE", ""),
    },
    "jwt": {
        "private_key": os.getenv("JWT_PRIVATE_KEY", ""),
    },
}

class VerifiedUser(BaseModel):
    """Represents a verified user."""

    user_id: str
    apple_id: str

DEV_JWT_SECRET = os.getenv("DEV_JWT_SECRET", "")

def create_dev_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(days=30),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        payload,
        DEV_JWT_SECRET,
        algorithm=algorithm,
    )

async def get_dev_user(token: str = Security(oauth2_scheme)) -> VerifiedUser:
    try:
        payload = jwt.decode(token, DEV_JWT_SECRET, algorithms=["HS256"])
        return VerifiedUser(user_id=payload["sub"], apple_id=payload["sub"])
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired token.",
        ) from err
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid ID token.")

class KafkaMessageTypes(IntEnum):
    NOTIFICATION = 0
    BOOP = 1
    MATCH = 2
    CHAT = 3


class SimpleUserResponse(BaseModel):
    """Response model for a single blocked user."""

    user_id: str
    profile_photo: str | None = None
    username: str | None = None
    display_name: str | None = None
    created_at: datetime


class NotificationEvent(BaseModel):
    """Represents the event for a notification."""

    notification_type: str
    reference_id: str
    post_type: str | None = None
    target_user_id: str
    action_user_id: str
    content_preview: str | None = None
    reference_node_id: str


class NotificationGroup(BaseModel):
    notification_id: str
    notification_type: str
    reference_id: str
    content_preview: str | None = None
    post_type: str | None = None
    action_users: list[SimpleUserResponse]
    action_count: int
    is_read: bool
    updated_at: datetime


class NotificationResponse(BaseModel):
    notifications: list[NotificationGroup]
    has_more: bool
    next_cursor: datetime | None = None


class GeneralKafkaWebsocketMessage(BaseModel):
    topic: str
    message: str


class EmbeddingSettings(BaseModel):
    """Represents the settings for embedding."""

    deployment_name: str
    dimensions: int
    version: str
    encoding_format: str = "float"
    model: str = "text-embedding-3-large"
    resource: str


class AzureOpenAISettings(BaseModel):
    """Represents the settings for Azure OpenAI."""

    api_key: str
    endpoint: str
    embedding: EmbeddingSettings


class AzureStorageSettings(BaseModel):
    """Represents the settings for Azure Storage."""

    account_key: str
    connection_string: str
    url: str
    name: str


class AzureSettings(BaseModel):
    """Represents the settings for Azure."""

    openai: AzureOpenAISettings
    storage: AzureStorageSettings


class JWTSettings(BaseModel):
    """Represents the settings for JWT."""

    private_key: str


class Neo4jSettings(BaseModel):
    """Represents the settings for Neo4j."""

    uri: str
    username: str
    password: str
    database: str


class KafkaSettings(BaseModel):
    """Represents the settings for Kafka."""

    connection_string: str


class AppleSettings(BaseModel):
    """Represents the settings for Apple."""

    key_id: str
    team_id: str
    client_id: str
    client_secret: str
    private_key: str
    auth_token_url: str
    auth_keys_url: str
    issuer: str
    authorization_url: str


class Settings(BaseModel):
    """Represents the settings for the application."""

    apple: AppleSettings = AppleSettings(
        key_id=apple_key_id,
        team_id=apple_developer_team_id,
        client_id=apple_client_id,
        client_secret=apple_client_secret,
        private_key=apple_private_key,
        auth_token_url=apple_auth_token_url,
        auth_keys_url=apple_auth_keys_url,
        issuer=apple_issuer,
        authorization_url=apple_authorization_url,
    )
    kafka: KafkaSettings = KafkaSettings(
        connection_string=kafka_connection_string,
    )
    azure: AzureSettings = AzureSettings(
        openai=AzureOpenAISettings(
            api_key=azure_openai_api_key,
            endpoint=azure_openai_endpoint,
            embedding=EmbeddingSettings(
                deployment_name=azure_openai_embedding_deployment_name,
                dimensions=int(azure_openai_embedding_dimensions),
                version=azure_openai_embedding_api_version,
                encoding_format=azure_openai_embedding_encoding_format,
                model=azure_openai_embedding_model,
                resource=azure_openai_embedding_resource,
            ),
        ),
        storage=AzureStorageSettings(
            account_key=azure_storage_account_key,
            connection_string=azure_storage_connection_string,
            url=azure_storage_url,
            name=azure_storage_account_name,
        ),
    )
    neo4j: Neo4jSettings = Neo4jSettings(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database,
    )
    jwt: JWTSettings = JWTSettings(
        private_key=jwt_private_key,
    )


settings_model = Settings()
driver = AsyncGraphDatabase.driver(
    str(settings["neo4j"]["uri"]),
    auth=(settings["neo4j"]["username"], settings["neo4j"]["password"]),
)
private_key = serialization.load_pem_private_key(
    str(settings["jwt"]["private_key"]).encode(),
    password=None,
    backend=default_backend(),
)

public_key = private_key.public_key()
pem_public_key = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


class ApplePublicKeyCache:
    """Cache for Apple public keys."""

    def __init__(self: "ApplePublicKeyCache") -> None:
        """Initialize the cache."""
        self.keys: list[dict[str, str]] | None = None
        self.expiry = datetime.min

    async def get_keys(self: "ApplePublicKeyCache") -> list[dict[str, str]]:
        """Fetch and return Apple public keys. Refresh if expired or not set."""
        if self.keys is None or datetime.now(UTC) >= self.expiry:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.get(str(settings["apple"]["auth_keys_url"]))
                key_data = response.json()
                self.keys = key_data["keys"]
                self.expiry = datetime.now(UTC) + timedelta(hours=24)
        return self.keys if self.keys is not None else []


key_cache = ApplePublicKeyCache()


class AppleTokenResponse(BaseModel):
    """Represents the response structure for an Apple token request.

    Attributes:
        access_token (str): The access token issued by Apple.
        token_type (str): The type of token, typically "Bearer".
        expires_in (str): The expiration time of the access token in seconds.
        refresh_token (str): The refresh token used to obtain a new access token.
        id_token (str): The ID token containing user information.
    """

    access_token: str
    token_type: str
    expires_in: str
    refresh_token: str
    id_token: str


class AppleTokenRequest(BaseModel):
    """Represents the request structure for an Apple token request.

    Attributes:
        client_id (str): The client ID for the Apple app.
        client_secret (str): The client secret for the Apple app.
        code (str): The authorization code received from Apple.
        grant_type (str): The type of grant, default is "authorization_code".
    """

    client_id: str = str(settings["apple"]["client_id"])
    client_secret: str = str(settings["apple"]["client_secret"])
    code: str
    grant_type: str = "authorization_code"


async def generate_client_secret(user_id: str) -> str:
    """Generate a client JWT for Apple Request.

    Args:
        user_id (str): The user ID to include in the JWT.

    Returns:
        str: A JWT token to be used as the client secret.

    Raises:
        jwt.PyJWTError: If there's an error encoding the JWT.
    """
    now = datetime.now(UTC)
    expiration_time = now + timedelta(minutes=5)

    headers = {"kid": str(settings["apple"]["key_id"])}

    payload = {
        "iss": str(settings["apple"]["team_id"]),
        "iat": now,
        "exp": expiration_time,
        "aud": str(settings["apple"]["issuer"]),
        "sub": str(settings["apple"]["client_id"]),
        "user_id": user_id,
    }

    return jwt.encode(
        payload,
        str(settings["jwt"]["secret"]),
        algorithm=str(settings["auth"]["algorithm"]),
        headers=headers,
    )


async def exchange_auth_code(code: str, user_id: str) -> AppleTokenResponse:
    """Request an access token from Apple using an authorization code.

    Args:
        code (str): The authorization code received from Apple.
        user_id (str): The user ID to include in the JWT.

    Returns:
        AppleTokenResponse: The response containing access token and related \
            information.

    Raises:
        HTTPException: If the exchange fails or the response status is not 200.
    """
    client_secret = await generate_client_secret(user_id)
    apple_token_request = AppleTokenRequest(code=code)

    data = {
        "client_id": apple_token_request.client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": apple_token_request.grant_type,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        response = await client.post(
            str(settings["apple"]["auth_token_url"]),
            data=data,
        )

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=400,
            detail="Exchange failure",
        )
    return AppleTokenResponse(**response.json())


async def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify the ID token received from Apple.

    Args:
        id_token (str): The ID token to verify.

    Returns:
        dict[str, Any]: The decoded token payload.

    Raises:
        HTTPException: If the token is invalid or verification fails.
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            key_response = await client.get(
                str(settings["apple"]["auth_keys_url"]),
            )
        key_data = key_response.json()
        jwk_key = key_data["keys"][0]
        public_key = RSAAlgorithm.from_jwk(jwk_key)

        # Ensure the public key is of type RSAPublicKey
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise HTTPException(status_code=400, detail="Invalid public key type.")

        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        decoded_token = jwt.decode(
            id_token,
            pem_public_key,
            algorithms=[str(settings["auth"]["algorithm"])],
            audience=str(settings["apple"]["client_id"]),
            issuer=str(settings["apple"]["issuer"]),
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired token.",
        ) from err
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID token.",
        ) from err
    else:
        return decoded_token


async def refresh_user_token(refresh_token: str, user_id: str) -> AppleTokenResponse:
    """Refresh the user's token.

    Args:
        refresh_token (str): The refresh token.
        user_id (str): The user's ID.

    Returns:
        AppleTokenResponse: The refreshed token.

    Raises:
        HTTPException: If the refresh fails or the response status is not 200.
    """
    client_secret = generate_client_secret(user_id)
    data = {
        "client_id": str(settings["apple"]["client_id"]),
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        response = await client.post(
            str(settings["apple"]["auth_token_url"]),
            data=data,
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=400,
            detail="Failed to refresh token",
        )
    return AppleTokenResponse(**response.json())


async def get_current_user(
    token: str = Security(oauth2_scheme),
) -> VerifiedUser:
    """Extract and verify user information from the JWT token.

    Args:
        token (str): The JWT token.

    Returns:
        VerifiedUser: The verified user information containing user_id and apple_id.

    Raises:
        HTTPException: If the token is invalid or verification fails.
    """
    try:
        if APP_ENV == "dev":
            return await get_dev_user(token)
        keys = await key_cache.get_keys()
        for jwk_key in keys:
            public_key = RSAAlgorithm.from_jwk(jwk_key)
            if not isinstance(public_key, rsa.RSAPublicKey):
                continue
            pem_public_key = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            try:
                decoded_token = jwt.decode(
                    token,
                    pem_public_key,
                    algorithms=[algorithm],
                    audience=str(settings["apple"]["client_id"]),
                    issuer=str(settings["apple"]["issuer"]),
                )
                user_id = decoded_token.get("user_id")
                apple_id = decoded_token.get("sub")
                if not user_id or not apple_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token payload.",
                    )
                return VerifiedUser(user_id=user_id, apple_id=apple_id)
            except jwt.ExpiredSignatureError as err:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Expired token.",
                ) from err
            except jwt.InvalidTokenError:
                continue
        raise HTTPException(status_code=400, detail="Invalid ID token.")
    except httpx.HTTPError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve Apple public keys.",
        ) from err


T = TypeVar("T", bound=BaseModel)


def create_partial_model(model_class: type[T], data: dict["str", Any]) -> T:
    """Create a partial Pydantic model instance from a dictionary of data.

    Args:
        model_class (Type[T]): The Pydantic model class to instantiate.
        data (dict): A dictionary containing the data to create the model instance.

    Returns:
        T: An instance of the specified Pydantic model.

    Raises:
        ValidationError: If the filtered data fails Pydantic's validation.
    """
    filtered_data = {k: v for k, v in data.items() if k in model_class.model_fields}
    return model_class(**filtered_data)


def parse_mentions(text: str) -> list[str]:
    """Extracts all mentions in the text.

    A mention is defined as a string that starts with '@' followed by alphanumeric
    characters and underscores.

    Args:
        text (str): The text to parse.

    Returns:
        List[str]: A list of mentions found in the text.
    """
    return re.findall(r"@(\w+)", text)


def parse_hashtags(text: str) -> list[str]:
    """Extracts all hashtags in the text.

    A hashtag is defined as a string that starts with '#' followed by alphanumeric
    characters and underscores.

    Args:
        text (str): The text to parse.

    Returns:
        List[str]: A list of hashtags found in the text.
    """
    return re.findall(r"#(\w+)", text)


class PostResponse(BaseModel):
    """Response model for getting a post."""

    post_id: str
    content: str
    created_at: datetime
    post_type: str
    is_video: bool
    video_url: str | None = None
    video_length: float | None = None
    like_count: int = 0
    view_count: int = 0
    attachments: list[str] | None = None
    quote_count: int = 0
    reply_count: int = 0
    repost_count: int = 0
    bookmark_count: int = 0
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    quoted_post: Optional["PostResponse"] | None = None
    replied_post: Optional["PostResponse"] | None = None
    reposted_post: Optional["PostResponse"] | None = None
    quoted_post_private: bool = False
    replied_post_private: bool = False
    reposted_post_private: bool = False
    post_embeddings: list[float] | None = []

    class Config:
        """Configures the model."""

        arbitrary_types_allowed = True


"--------------- USER ACCOUNT RELATED ROUTES ---------------"


class Religion(IntEnum):
    """Represents a user's religion."""

    ATHEISM = 0
    AGNOSTICISM = 1
    CHRISTIANITY = 2
    ISLAM = 3
    JUDAISM = 4
    HINDUISM = 5
    BUDDHISM = 6
    SIKHISM = 7
    TAOISM = 8
    SHINTO = 9
    PAGANISM = 10
    SPIRITUAL_BUT_NOT_RELIGIOUS = 11
    OTHER = 12
    PREFER_NOT_TO_SAY = 13


class Gender(IntEnum):
    """Represents a user's gender."""

    MALE = 0
    FEMALE = 1
    NON_BINARY = 2
    GENDERQUEER = 3
    GENDERFLUID = 4
    AGENDER = 5
    BIGENDER = 6
    TWO_SPIRIT = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class SexualOrientation(IntEnum):
    """Represents a user's sexual orientation."""

    HETEROSEXUAL = 0
    HOMOSEXUAL = 1
    BISEXUAL = 2
    PANSEXUAL = 3
    ASEXUAL = 4
    QUEER = 6
    QUESTIONING = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class RelationshipStatus(IntEnum):
    """Represents a user's relationship status."""

    SINGLE = 0
    IN_A_RELATIONSHIP = 1
    ENGAGED = 2
    MARRIED = 3
    DIVORCED = 4
    WIDOWED = 5
    COMPLICATED = 6
    OPEN_RELATIONSHIP = 7
    OTHER = 8
    PREFER_NOT_TO_SAY = 9


class EducationLevel(IntEnum):
    """Represents a user's education level."""

    HIGH_SCHOOL = 0
    SOME_COLLEGE = 1
    ASSOCIATES_DEGREE = 2
    BACHELORS_DEGREE = 3
    MASTERS_DEGREE = 4
    DOCTORATE = 5
    TRADE_SCHOOL = 6
    OTHER = 7
    PREFER_NOT_TO_SAY = 8


class LookingFor(IntEnum):
    """Represents a user's looking for."""

    FRIENDS = 0
    CASUAL_DATING = 1
    LONG_TERM_RELATIONSHIP = 2
    MARRIAGE = 3
    HOOKUP = 4
    FLING = 5
    SITUATIONSHIP = 6
    NEED_A_DATE_TO_EVENT = 7
    NETWORKING = 8
    ACTIVITY_PARTNERS = 9
    CHAT_BUDDIES = 10
    NOT_SURE = 11
    OTHER = 12
    PREFER_NOT_TO_SAY = 13


class School(BaseModel):
    """Represents a user's school."""

    name: str
    start_year: int
    end_year: int | None = None
    degree: str | None = None
    major: str | None = None


class Education(BaseModel):
    """Represents a user's education."""

    highest_level: EducationLevel
    schools: list[School] = []


class HasChildren(IntEnum):
    """Represents a user's children status."""

    NO = 0
    YES = 1
    PREFER_NO_TO_SAY = 2


class WantsChildren(IntEnum):
    """Represents a user's wants children status."""

    NEVER = 0
    SOMEDAY = 1
    YES = 2
    NOT_SURE = 3
    PREFER_NOT_TO_SAY = 4


class BasicUserResponse(BaseModel):
    """Response model for getting a basic user."""

    user_id: str
    apple_id: str
    email: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool = True
    account_private: bool = False
    username: str | None = None
    refresh_token: str | None = None
    following_count: int = 0
    followers_count: int = 0
    created_at: datetime | None = None
    last_login: datetime | None = None
    last_seen: datetime | None = None


class User(BaseModel):
    """Represents a basic user."""

    # Basic user information
    user_id: str
    apple_id: str
    email: str

    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool = True
    account_private: bool = False
    username: str | None = None
    refresh_token: str | None = None
    following_count: int = 0
    followers_count: int = 0
    profile_location: tuple[float, float] | None = None
    created_at: datetime | None = None
    last_login: datetime | None = None
    last_seen: datetime | None = None
    user_embeddings: list[float] | None = None

    # User traits
    introversion_extraversion: float | None = None
    thinking_feeling: float | None = None
    sensing_intuition: float | None = None
    judging_perceptive: float | None = None
    conscientiousness: float | None = None
    agreeableness: float | None = None
    neuroticism: float | None = None
    individualism_collectivism: float | None = None
    libertarianism_authoritarianism: float | None = None
    environmentalism_anthropocentrism: float | None = None
    isolationism_interventionism: float | None = None
    security_freedom: float | None = None
    noninterventionism_interventionism: float | None = None
    equity_meritocracy: float | None = None
    empathy: float | None = None
    honesty: float | None = None
    humility: float | None = None
    independence: float | None = None
    patience: float | None = None
    persistence: float | None = None
    playfulness: float | None = None
    rationality: float | None = None
    religiosity: float | None = None
    self_acceptance: float | None = None
    sex_focus: float | None = None
    thriftiness: float | None = None
    thrill_seeking: float | None = None
    drug_friendliness: float | None = None
    emotional_openness_in_relationships: float | None = None
    equanimity: float | None = None
    family_focus: float | None = None
    loyalty: float | None = None
    preference_for_monogamy: float | None = None
    trust: float | None = None
    self_esteem: float | None = None
    anxious_attachment: float | None = None
    avoidant_attachment: float | None = None
    career_focus: float | None = None
    emphasis_on_boundaries: float | None = None
    fitness_focus: float | None = None
    stability_of_self_image: float | None = None
    love_focus: float | None = None
    maturity: float | None = None
    wholesomeness: float | None = None
    traditionalist_view_of_love: float | None = None
    openness_to_experience: float | None = None

    # User astrology
    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None
    sun: str | None = None
    moon: str | None = None
    ascendant: str | None = None
    mercury: str | None = None
    venus: str | None = None
    mars: str | None = None
    jupiter: str | None = None
    saturn: str | None = None
    uranus: str | None = None
    neptune: str | None = None
    pluto: str | None = None

    # User dating profile options
    dating_active: bool
    recent_location: tuple[float, float]
    dating_photos: list[str] = []
    dating_bio: str = ""

    height: int | None = None
    gender: Gender
    sexual_orientation: SexualOrientation
    relationship_status: RelationshipStatus
    religion: Religion
    education: Education
    highest_education_level: EducationLevel
    looking_for: list[LookingFor]
    has_children: HasChildren
    wants_children: WantsChildren
    has_tattoos: bool

    # User dating profile flags
    show_gender: bool = True
    show_sexual_orientation: bool = True
    show_relationship_status: bool = True
    show_religion: bool = True
    show_education: bool = True
    show_looking_for: bool = True
    show_schools: bool = True
    show_has_children: bool = True
    show_wants_children: bool = True

    # User dating profile preferences
    max_distance: float = 10000
    minimum_age: int = 0
    maximum_age: int = 110
    minimum_height: int = 0
    maximum_height: int = 108
    gender_preferences: list[Gender] = []
    has_children_preferences: list[HasChildren] = []
    wants_children_preferences: list[WantsChildren] = []
    education_level_preferences: list[EducationLevel] = []
    religion_preferences: list[Religion] = []
    sexual_orientation_preferences: list[SexualOrientation] = []
    relationship_status_preferences: list[RelationshipStatus] = []
    looking_for_preferences: list[LookingFor] = []

    # Notifications Bells
    last_checked_boops: datetime | None = None
    last_checked_messages: datetime | None = None
    last_checked_notifications: datetime | None = None
    last_checked_dating: datetime | None = None
    last_checked_predictions: datetime | None = None
    last_checked_follow_requests: datetime | None = None


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    # We need to leave all fields as None to avoid overwriting existing values

    # Allowed fields to update: basic user information
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    header_photo: str | None = None
    profile_song: str | None = None
    account_active: bool | None = None
    account_private: bool | None = None
    username: str | None = None
    profile_location: tuple[float, float] | None = None
    profile_bio: str | None = None

    # Allowed fields to update: astrology
    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None

    # Allowed fields to update: dating profile
    dating_active: bool | None = None
    recent_location: tuple[float, float] | None = None
    dating_photos: list[str] | None = None
    dating_bio: str | None = None

    height: int | None = None
    gender: Gender | None = None
    sexual_orientation: SexualOrientation | None = None
    relationship_status: RelationshipStatus | None = None
    religion: Religion | None = None
    education: Education | None = None
    highest_education_level: EducationLevel | None = None
    looking_for: list[LookingFor] | None = None
    has_children: HasChildren | None = None
    wants_children: WantsChildren | None = None
    has_tattoos: bool | None = None

    # Allowed fields to update: dating profile preferences
    max_distance: float | None = None
    minimum_age: int | None = None
    maximum_age: int | None = None
    minimum_height: int | None = None
    maximum_height: int | None = None
    gender_preferences: list[Gender] | None = None
    has_children_preferences: list[HasChildren] | None = None
    wants_children_preferences: list[WantsChildren] | None = None
    education_level_preferences: list[EducationLevel] | None = None
    religion_preferences: list[Religion] | None = None
    sexual_orientation_preferences: list[SexualOrientation] | None = None
    relationship_status_preferences: list[RelationshipStatus] | None = None
    looking_for_preferences: list[LookingFor] | None = None


class DetailedDatingProfileResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_photo: str | None = None
    account_private: bool
    username: str
    distance: float | None = None
    dating_photos: list[str] | None = None
    dating_bio: str | None = None
    height: int | None = None
    gender: Gender | None = None
    sexual_orientation: SexualOrientation | None = None
    relationship_status: RelationshipStatus | None = None
    religion: Religion | None = None
    # education: Education | None = None
    highest_education_level: EducationLevel | None = None
    looking_for: list[LookingFor] | None = None
    has_children: HasChildren | None = None
    wants_children: WantsChildren | None = None
    has_tattoos: bool | None = None


class UserProfileResponse(BaseModel):
    """Response model for getting a user's profile."""

    user: BasicUserResponse
    posts: list[PostResponse]
    follows_user: bool
    has_swiped_right: bool
    has_swiped_left: bool
    has_more: bool
    next_cursor: datetime | None = None
    is_private: bool = False


@router.get("/api/user/profile/{target_user_id}", response_model=UserProfileResponse)
async def get_user_route(
    target_user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> UserProfileResponse:
    """Get the user profile for a user.

    Args:
        target_user_id (str): The ID of the user being requested.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of posts to return. Defaults to 10.
        verified_user (VerifiedUser): The user doing the request.

    Returns:
        UserProfileResponse: The user profile for the user.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (requesting_user:User {user_id: $requesting_user_id})
    MATCH (target_user:User {user_id: $target_user_id})

    // Check if either user has blocked the other
    OPTIONAL MATCH (requesting_user)-[:BLOCKS]-(target_user)
    WITH requesting_user, target_user, COUNT(DISTINCT target_user) AS block_count

    // Check if requesting user follows the target user
    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(target_user)
    WITH requesting_user, target_user, block_count, COUNT(DISTINCT target_user) AS following_count

    // Check if requesting user has swiped on the target user
    OPTIONAL MATCH (requesting_user)-[swiped_right:SWIPED_RIGHT]->(target_user)
    OPTIONAL MATCH (requesting_user)-[swiped_left:SWIPED_LEFT]->(target_user)

    WHERE block_count = 0

    // Fetch posts created by the target user with pagination
    OPTIONAL MATCH (target_user)-[r:POSTED|QUOTED|REPLIED|REPOSTED]->(post:Post)
    WHERE (target_user.account_private = FALSE OR following_count > 0) AND r.created_at < $cursor
    WITH target_user, post, r, following_count, target_user.account_private AS account_private, swiped_right, swiped_left
    ORDER BY r.created_at DESC
    LIMIT $limit + 1

    // Fetch related posts for QUOTED, REPLIED, and REPOSTED
    OPTIONAL MATCH (post)<-[quoted:QUOTED]-(quoted_post:Post)
    OPTIONAL MATCH (post)<-[replied:REPLIED]-(replied_post:Post)
    OPTIONAL MATCH (post)<-[reposted:REPOSTED]-(reposted_post:Post)

    // Check if the quoted or replied posts are from private users not followed by the requesting user
    OPTIONAL MATCH (quoted_post_user:User)-[:POSTED]->(quoted_post)
    OPTIONAL MATCH (replied_post_user:User)-[:POSTED]->(replied_post)
    OPTIONAL MATCH (reposted_post_user:User)-[:POSTED]->(reposted_post)

    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(quoted_post_user) AS follows_quoted_user
    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(replied_post_user) AS follows_replied_user
    OPTIONAL MATCH (requesting_user)-[:FOLLOWS]->(reposted_post_user) AS follows_reposted_user

    RETURN target_user {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        .header_photo,
        .account_private,
        .dating_active,
        .following_count,
        .followers_count,
        .profile_song
    } AS user,
    collect({
        post_id: post.post_id,
        content: post.content,
        created_at: r.created_at,
        type: type(r),
        quoted_post: CASE WHEN type(r) = 'QUOTED' THEN quoted_post { .post_id, .content, .created_at } ELSE NULL END,
        replied_post: CASE WHEN type(r) = 'REPLIED' THEN replied_post { .post_id, .content, .created_at } ELSE NULL END,
        reposted_post: CASE WHEN type(r) = 'REPOSTED' THEN reposted_post { .post_id, .content, .created_at } ELSE NULL END,
        quoted_post_private: CASE WHEN type(r) = 'QUOTED' THEN quoted_post_user.account_private AND follows_quoted_user IS NULL ELSE NULL END,
        replied_post_private: CASE WHEN type(r) = 'REPLIED' THEN replied_post_user.account_private AND follows_replied_user IS NULL ELSE NULL END,
        reposted_post_private: CASE WHEN type(r) = 'REPOSTED' THEN reposted_post_user.account_private AND follows_reposted_user IS NULL ELSE NULL END
    }) AS posts,
    following_count > 0 AS follows_user,
    swiped_right IS NOT NULL AS has_swiped_right,
    swiped_left IS NOT NULL AS has_swiped_left,
    (target_user.account_private AND following_count = 0) AS is_private
    """  # noqa: E501

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": verified_user.user_id,
                "target_user_id": target_user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        data = await result.single()

        if not data:
            raise HTTPException(
                status_code=404,
                detail="User not found or access denied",
            )

        user_data = data["user"]
        posts_data = data["posts"]
        follows_user = data["follows_user"]
        has_swiped_right = data["has_swiped_right"]
        has_swiped_left = data["has_swiped_left"]
        is_private = data["is_private"]

        user = BasicUserResponse(**user_data)
        posts = [PostResponse(**post) for post in posts_data[:limit]] if not is_private else []
        has_more = len(posts_data) > limit
        next_cursor = posts[-1].created_at if posts else None

        return UserProfileResponse(
            user=user,
            posts=posts,
            follows_user=follows_user,
            has_swiped_right=has_swiped_right,
            has_swiped_left=has_swiped_left,
            has_more=has_more,
            next_cursor=next_cursor,
            is_private=is_private,
        )


class CreateUserResponse(BaseModel):
    """Response model for creating a new user."""

    user_id: str
    apple_id: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    display_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    created_at: datetime
    last_login: datetime


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing a user's access token."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for a user's access token."""

    access_token: str
    refresh_token: str
    token_id: str

@router.post("/api/dev/user", response_model=CreateUserResponse)
async def create_dev_user_route(

) -> CreateUserResponse:
    """Create a new user for development purposes.
    """
    user_id = str(uuid4())
    apple_id = f"fake-apple-id-{user_id}"
    email = f"testuser{user_id}@example.com"
    first_name = "Test"
    last_name = "User"
    now = datetime.now(UTC)

    query = """
    MERGE (user:User {apple_id: $apple_id})
    ON CREATE SET
        user.user_id = $user_id,
        user.apple_id = $apple_id,
        user.email = $email,
        user.first_name = $first_name,
        user.last_name = $last_name,
        user.created_at = $created_at,
        user.last_login = $last_login
    ON MATCH SET
        user.last_login = $last_login
    RETURN user
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "apple_id": apple_id,
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": now.isoformat(),
                "last_login": now.isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed.",
            )
        user_data = record["user"]
        access_token = create_dev_jwt(user_id)
        return CreateUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=user_data["email"],
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            username=user_data.get("username", None),
            display_name=user_data.get("display_name", None),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
            access_token=access_token,
            refresh_token=None,
        )

@router.post("/api/user", response_model=CreateUserResponse)
async def create_user_route(
    apple_token: str = Depends(oauth2_scheme),
) -> CreateUserResponse:
    """Create a new user after successful Apple authentication.

    Args:
        apple_token (str): The OAuth2 token received from Apple.

    Returns:
        CreateUserResponse: The response containing the created user details.
    """
    try:
        # Verify the id_token with Apple and get user info
        user_info = await verify_id_token(apple_token)
        # Exchange the authorization code for access and refresh tokens
        apple_token_response = await exchange_auth_code(apple_token, user_info["sub"])
    except HTTPException as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Apple token.",
        ) from err

    apple_id = user_info["sub"]
    email = user_info["email"]
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    apple_refresh_token = apple_token_response.refresh_token

    user_id = str(uuid4())
    token_id = str(uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=30)

    query = """
        MERGE (user:User {apple_id: $apple_id})
        ON CREATE SET
            user.user_id = $user_id,
            user.apple_id = $apple_id,
            user.email = $email,
            user.first_name = $first_name,
            user.last_name = $last_name,
            user.created_at = $created_at,
            user.last_login = $last_login
        ON MATCH SET
            user.last_login = $last_login
        WITH user
        CREATE (user)-[:HAS_REFRESH_TOKEN {
            token_id: $token_id,
            refresh_token: $apple_refresh_token,
            created_at: $created_at,
            expires_at: $expires_at
        }]->(token:Token)
        RETURN user, token
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "apple_id": apple_id,
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "apple_refresh_token": apple_refresh_token,
                "token_id": token_id,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_login": now.isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed.",
            )
        user_data = record["user"]
        # Generate access token
        access_token = jwt.encode(
            {
                "sub": user_id,
                "exp": datetime.now(UTC) + timedelta(minutes=15),  # Access token expiry
                "user_id": user_id,
            },
            str(settings["jwt"]["private_key"]),
            algorithm="RS256",
        )
        return CreateUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=user_data["email"],
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            username=user_data.get("username", None),
            display_name=user_data.get("display_name", None),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
            access_token=access_token,
            refresh_token=apple_refresh_token,
        )


@router.put("/api/user", response_model=BasicUserResponse)
async def update_user_route(
    user_updates: UpdateUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BasicUserResponse:
    """Updates user information.

    Args:
        user_updates (UpdateUserRequest): The request body containing user updates.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        BasicUserResponse: The updated user information.
    """
    user_id = verified_user.user_id

    # Construct the SET clause dunamically based on provided fields
    set_clauses: list[str] = []
    params = {
        "user_id": user_id,
    }

    for field, value in user_updates.model_dump(exclude_unset=True).items():
        set_clauses.append(f"user.{field} = ${field}")
        params[field] = value

    set_clause = ", ".join(set_clauses)

    query = cast(
        LiteralString,
        f"""
        MATCH (user:User {{user_id: $user_id}})
        SET {set_clause}
        RETURN user
    """,
    )

    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        user_data = record["user"]
        return BasicUserResponse(
            user_id=user_data["user_id"],
            apple_id=user_data["apple_id"],
            email=user_data.get("email", None),
            first_name=user_data.get("first_name", None),
            last_name=user_data.get("last_name", None),
            profile_photo=user_data.get("profile_photo", None),
            header_photo=user_data.get("header_photo", None),
            profile_song=user_data.get("profile_song", None),
            account_active=user_data.get("account_active", True),
            account_private=user_data.get("account_private", False),
            username=user_data.get("username", None),
            following_count=user_data.get("following_count", 0),
            followers_count=user_data.get("followers_count", 0),
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]),
        )


@router.delete("/api/user")
async def delete_user_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> dict[str, str]:
    """Delete the authenticated user's account.

    Args:
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or deletion fails.

    Returns:
        dict[str, str]: A message confirming the deletion.
    """
    user_id = verified_user.user_id

    query = """
    MATCH (user:User {user_id: $user_id})
    DETACH DELETE user
    RETURN COUNT(user) AS count
    """

    async with driver.session() as session:
        result = await session.run(query, {"user_id": user_id})
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User deletion failed",
            )

        if record["count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    return {"message": "User account deleted successfully"}


"--------------- USER AUTHENTICATION -----------------"


@router.post("/api/user/refresh", response_model=TokenResponse)
async def refresh_user_route(token_data: RefreshTokenRequest) -> TokenResponse:
    """Refresh the user's access token.

    Args:
        token_data (RefreshTokenRequest): The request containing the refresh token.

    Returns:
        TokenResponse: The response containing the access token and refresh token.
    """
    refresh_token = token_data.refresh_token
    try:
        decoded_token = jwt.decode(
            refresh_token,
            pem_public_key,  # Verify with the public key
            algorithms=["RS256"],  # Assuming RS256 was used to sign the token
            audience=settings["apple"]["client_id"],
            issuer=str(settings["apple"]["issuer"]),
        )
        user_id = decoded_token.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )

        # Generate a new access token
        access_token = jwt.encode(
            {
                "sub": user_id,
                "exp": datetime.now(UTC) + timedelta(minutes=15),  # Access token expiry
                "user_id": user_id,
            },
            str(settings["jwt"]["private_key"]),
            algorithm="RS256",
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Return the existing refresh token
            token_id=str(uuid4()),  # Generate a new token_id for the response
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired token.",
        ) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        ) from err


"--------------- CHECK USERNAME AVAILABILITY -----------------"


class UsernameCheckResponse(BaseModel):
    """Response model for checking username availability."""

    username_exists: bool


@router.get("/api/user/username/{username}", response_model=UsernameCheckResponse)
async def check_username_route(username: str) -> UsernameCheckResponse:
    """Check if a username is available.

    Args:
        username (str): The username to check.

    Returns:
        UsernameCheckResponse: The response containing the availability status.
    """
    query = """
    MATCH (user:User {username: $username})
    RETURN user.username AS username
    """

    async with driver.session() as session:
        result = await session.run(query, {"username": username})
        record = await result.single()
        if not record:
            return UsernameCheckResponse(username_exists=False)
        return UsernameCheckResponse(username_exists=True)


"--------------- USER BLOCKS -----------------"


class WasSuccessfulResponse(BaseModel):
    """Response model for basic success."""

    successful: bool


class BlockedUsersResponse(BaseModel):
    """Response model for getting a list of blocked users."""

    blocked_list: list[SimpleUserResponse]


@router.get("/api/user/block", response_model=BlockedUsersResponse)
async def get_block_list_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BlockedUsersResponse:
    """Get a list of blocked users."""
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})-[r:BLOCKS]->(blocked_user:User)
    RETURN blocked_user.user_id AS user_id,
        blocked_user.profile_photo AS profile_photo,
        blocked_user.username AS username,
        blocked_user.display_name AS display_name,
        r.created_at AS created_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No blocked users found.",
            )
        return BlockedUsersResponse(
            blocked_list=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["blocked_list"]
            ],
        )


class BlockUserRequest(BaseModel):
    """Request model for blocking a user."""

    user_id: str


@router.post("/api/user/block", response_model=WasSuccessfulResponse)
async def block_user_route(
    request: BlockUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Block a user.

    Args:
        request (BlockUserRequest): The request containing the user ID to block.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was blocked.
    """
    user_id = request.user_id
    user_id = verified_user.user_id

    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (blocked_user:User {user_id: $blocked_user_id})
    MERGE (user)-[r:BLOCKS {created_at: $created_at}]->(blocked_user)
    WITH user, blocked_user
    OPTIONAL MATCH (user)-[f1:FOLLOWS]->(blocked_user)
    OPTIONAL MATCH (blocked_user)-[f2:FOLLOWS]->(user)
    DELETE f1, f2
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "blocked_user_id": request.user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/user/block/{user_id}", response_model=WasSuccessfulResponse)
async def unblock_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unblock a user.

    Args:
        user_id (str): The user ID to unblock.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was unblocked.
    """
    user_id = verified_user.user_id

    query = """
    MATCH (user:User {user_id: $user_id})-[r:BLOCKS]->(blocked_user:User {user_id: $blocked_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "blocked_user_id": user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- USER MUTES -----------------"


class MutedUsersResponse(BaseModel):
    """Response model for getting a list of muted users."""

    muted_list: list[SimpleUserResponse]


@router.get("/api/user/mute")
async def get_mute_list_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> MutedUsersResponse:
    """Get a list of muted users.

    Args:
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the request fails.

    Returns:
        MutedUsersResponse: The response containing the list of muted users.
    """
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})-[r:MUTES]->(muted_user:User)
    RETURN muted_user.user_id AS user_id,
        muted_user.profile_photo AS profile_photo,
        muted_user.username AS username,
        muted_user.display_name AS display_name,
        r.created_at AS created_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No muted users found.",
            )
        return MutedUsersResponse(
            muted_list=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["muted_list"]
            ],
        )


class MuteUserRequest(BaseModel):
    """Request model for muting a user."""

    user_id: str


@router.post("/api/user/mute", response_model=WasSuccessfulResponse)
async def mute_user_route(
    request: MuteUserRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Mute a user.

    Args:
        request (MuteUserRequest): The request containing the user ID to mute.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was muted.
    """
    query = """
    MATCH (user:User {user_id: $user_id})
    MERGE (user)-[r:MUTES {created_at: $created_at}]->(muted_user:User {user_id: $muted_user_id})
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "muted_user_id": request.user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/user/mute/{user_id}", response_model=WasSuccessfulResponse)
async def unmute_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unmute a user.

    Args:
        user_id (str): The user ID to unmute.
        verified_user: The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was unmuted.
    """
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})-[r:MUTES]->(muted_user:User {user_id: $muted_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "muted_user_id": user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- USER FOLLOWS -----------------"


class FollowingResponse(BaseModel):
    """Response model for getting a list of followed users."""

    user_follows: list[SimpleUserResponse]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/user/follows/{user_id}", response_model=FollowingResponse)
async def get_following_route(
    user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> FollowingResponse:
    """Get a list of followed users.

    Args:
        user_id (str): The user ID to get the followed users for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of follows to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        FollowingResponse: The response containing the list of followed users.
    """
    cursor = cursor or datetime.now(UTC)

    # Skip privacy and block checks if the user is checking their own profile
    if user_id != verified_user.user_id:
        # Check if the target user is private and if the requesting user follows them
        check_private_and_follows_query = """
        MATCH (target_user:User {user_id: $target_user_id})
        OPTIONAL MATCH (requesting_user:User {user_id: $requesting_user_id})-[:FOLLOWS]->(target_user)
        OPTIONAL MATCH (requesting_user)-[:BLOCKS]-(target_user)
        RETURN target_user.account_private AS is_private, COUNT(DISTINCT requesting_user) > 0 AS follows, COUNT(DISTINCT target_user) = 0 AS blocked
        """  # noqa: E501

        async with driver.session() as session:
            check_result = await session.run(
                check_private_and_follows_query,
                {
                    "target_user_id": user_id,
                    "requesting_user_id": verified_user.user_id,
                },
            )
            check_data = await check_result.single()
            if not check_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )

            is_private = check_data["is_private"]
            follows = check_data["follows"]
            blocked = check_data["blocked"]

            if blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You have blocked this user.",
                )
            if is_private and not follows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User profile is private.",
                )

    # Query to fetch the follows with pagination and sorting
    fetch_follows_query = """
    MATCH (user:User {user_id: $user_id})-[:FOLLOWS]->(followed_user:User)
    WHERE followed_user.created_at < $cursor
    RETURN followed_user {
        .user_id,
        .profile_photo,
        .username,
        .display_name,
        .created_at
    } AS followed_user
    ORDER BY followed_user.created_at DESC
    LIMIT $limit + 1
    """

    async with driver.session() as session:
        fetch_result = await session.run(
            fetch_follows_query,
            {
                "user_id": user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        follows_data = await fetch_result.data()

        follows_list = [
            SimpleUserResponse(
                user_id=user["followed_user"]["user_id"],
                profile_photo=user["followed_user"].get("profile_photo"),
                username=user["followed_user"].get("username"),
                display_name=user["followed_user"].get("display_name"),
                created_at=datetime.fromisoformat(user["followed_user"]["created_at"]),
            )
            for user in follows_data[:limit]  # Only take up to the limit
        ]

        has_more = len(follows_data) > limit
        next_cursor = follows_data[limit - 1]["followed_user"]["created_at"] if has_more else None

    return FollowingResponse(
        user_follows=follows_list,
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.delete("/api/user/follows/{user_id}", response_model=WasSuccessfulResponse)
async def unfollow_user_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unfollow a user.

    Args:
        user_id (str): The user ID to unfollow.
        verified_user: The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the user was unfollowed.
    """
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})-[r:FOLLOWS]->(followed_user:User {user_id: $followed_user_id})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "followed_user_id": user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return WasSuccessfulResponse(successful=True)


class FollowRequestReponse(BaseModel):
    """Response model for getting a list of follow requests."""

    user_follow_requests: list[SimpleUserResponse]


@router.get("/api/user/follow-requests", response_model=FollowRequestReponse)
async def get_follow_requests_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> FollowRequestReponse:
    """Get a list of follow requests.

    Args:
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If no follow requests are found.

    Returns:
        FollowRequestReponse: The response containing the list of follow requests.

    """
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})-[r:FOLLOW_REQUEST]->(followed_user:User)
    RETURN followed_user.user_id AS user_id,
        followed_user.profile_photo AS profile_photo,
        followed_user.username AS username,
        followed_user.display_name AS display_name,
        r.created_at AS created_at
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
            },
        )
        data = await result.single()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No follow requests found.",
            )
        return FollowRequestReponse(
            user_follow_requests=[
                SimpleUserResponse(
                    user_id=user_data["user_id"],
                    profile_photo=user_data.get("profile_photo", None),
                    username=user_data.get("username", None),
                    display_name=user_data.get("display_name", None),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                )
                for user_data in data["user_follow_requests"]
            ],
        )


class SendFollowReqRequest(BaseModel):
    """Request model for sending a follow request."""

    user_id: str


@router.post("/api/user/follow-requests", response_model=WasSuccessfulResponse)
async def send_follow_request_route(
    request: SendFollowReqRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Send a follow request.

    Args:
        request (SendFollowReqRequest): The request containing the user ID to send the follow request to.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the follow request was sent.
    """
    user_id = verified_user.user_id
    target_user_id = request.user_id

    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (target_user:User {user_id: $target_user_id})
    OPTIONAL MATCH (user)-[:BLOCKS]->(target_user)
    OPTIONAL MATCH (target_user)-[:BLOCKS]->(user)
    WITH user, target_user, COUNT(DISTINCT user) AS user_blocks, COUNT(DISTINCT target_user) AS target_user_blocks
    WHERE user_blocks = 0 AND target_user_blocks = 0
    RETURN target_user.account_private AS is_private
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "target_user_id": target_user_id,
            },
        )
        record = await result.single()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or blocked.",
            )

        is_private = record["is_private"]

        if is_private:
            relationship_query = """
            MATCH (user:User {user_id: $user_id})
            MATCH (target_user:User {user_id: $target_user_id})
            MERGE (user)-[r:FOLLOW_REQUEST {created_at: $created_at}]->(target_user)
            RETURN r
            """
        else:
            relationship_query = """
            MATCH (user:User {user_id: $user_id})
            MATCH (target_user:User {user_id: $target_user_id})
            MERGE (user)-[r:FOLLOWS {created_at: $created_at}]->(target_user)
            RETURN r
            """

        result = await session.run(
            relationship_query,
            {
                "user_id": user_id,
                "target_user_id": target_user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow request.",
            )
        return WasSuccessfulResponse(successful=True)


@router.delete(
    "/api/user/follow-requests/{received_from_user_id}",
    response_model=WasSuccessfulResponse,
)
async def delete_follow_request_route(
    received_from_user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete/deny a follow request received from a user.

    Args:
        received_from_user_id (str): The user ID to delete the follow request for.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or the request fails.

    Returns:
        WasSuccessfulResponse: The response indicating whether the follow request was deleted.
    """
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user})-[r:FOLLOW_REQUEST]->(target_user:User {user_id: $target_user})
    DELETE r
    RETURN r
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user": user_id,
                "target_user": received_from_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or follow request not found.",
            )
        return WasSuccessfulResponse(successful=True)


class GetFollowersResponse(BaseModel):
    """Response model for getting a list of followers."""

    followers: list[SimpleUserResponse]
    has_more: bool
    last_follow_datetime: datetime | None = None


@router.get("/api/user/followers/{user_id}", response_model=GetFollowersResponse)
async def get_followers_route(
    user_id: str,
    cursor: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> GetFollowersResponse:
    """Get a list of followers for a user.

    Args:
        user_id (str): The user ID to get the followers for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        skip (int, optional): The number of followers to skip. Defaults to 0.
        limit (int, optional): The number of followers to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        GetFollowersResponse: The response containing the list of followers.
    """
    cursor = cursor or datetime.now(UTC)

    if user_id == verified_user.user_id:
        # Bypass privacy/blocked checks if the user is checking their own follower list
        query = """
        MATCH (user:User {user_id: $user_id})<-[:FOLLOWS]-(follower:User)
        WHERE follower.created_at < $cursor
        RETURN follower {
            .user_id,
            .profile_photo,
            .username,
            .display_name,
            .created_at
        } AS follower
        ORDER BY follower.created_at DESC
        SKIP $skip LIMIT $limit
        """
    else:
        # Perform privacy and blocked checks for other users
        query = """
        MATCH (user:User {user_id: $user_id})
        MATCH (user)<-[:FOLLOWS]-(follower:User)
        OPTIONAL MATCH (user)-[:BLOCKS]-(follower)
        OPTIONAL MATCH (follower)-[:BLOCKS]-(user)
        WITH user, follower, COUNT(DISTINCT user) AS user_blocks, COUNT(DISTINCT follower) AS follower_blocks
        WHERE user.account_private = FALSE OR (user.account_private = TRUE AND (user)-[:FOLLOWS]->(follower))
        AND user_blocks = 0 AND follower_blocks = 0
        AND follower.created_at < $cursor
        RETURN follower {
            .user_id,
            .profile_photo,
            .username,
            .display_name,
            .created_at
        } AS follower
        ORDER BY follower.created_at DESC
        SKIP $skip LIMIT $limit
        """

    async with driver.session() as session:
        fetch_result = await session.run(
            query,
            {
                "user_id": user_id,
                "cursor": cursor.isoformat(),
                "skip": skip,
                "limit": limit,
            },
        )
        followers_data = await fetch_result.data()

        if not followers_data:
            return GetFollowersResponse(
                followers=[],
                has_more=False,
                last_follow_datetime=None,
            )

        followers_list = [
            SimpleUserResponse(
                user_id=user["follower"]["user_id"],
                profile_photo=user["follower"].get("profile_photo"),
                username=user["follower"].get("username"),
                display_name=user["follower"].get("display_name"),
                created_at=datetime.fromisoformat(user["follower"]["created_at"]),
            )
            for user in followers_data
        ]

        return GetFollowersResponse(
            followers=followers_list,
            has_more=len(followers_list) == limit,
            last_follow_datetime=(datetime.fromisoformat(followers_data[-1]["follower"]["created_at"]) if followers_list else None),
        )


class GetFollowRecommendationsResponse(BaseModel):
    """Response model for getting a list of users that the user may want to follow."""

    recommendations: list[SimpleUserResponse]


@router.get(
    "/api/user/recommendations",
    response_model=GetFollowRecommendationsResponse,
)
async def get_follow_recommendations_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> GetFollowRecommendationsResponse:
    """Get a list of users that the user may want to follow.

    Args:
        verified_user (VerifiedUser): The user making the request.

    Returns:
        GetFollowRecommendationsResponse: The list of users that the user may want to follow.
    """
    query = """
    MATCH (user:User {user_id: $user_id, account_active: True})
    MATCH (potential_follow:User {account_active: True})
    WHERE NOT (user)-[:FOLLOWS]->(potential_follow)
    AND user <> potential_follow
    AND NOT (user)-[:BLOCKS]-(potential_follow)
    AND NOT (user)-[:MUTES]->(potential_follow)
    AND NOT (potential_follow)-[:MUTES]->(user)
    // Common Follows
    OPTIONAL MATCH (user)-[:FOLLOWS]->(common_follow:User)-[:FOLLOWS]->(potential_follow)
    WITH user, potential_follow, COUNT(DISTINCT common_follow) AS common_follows_count
    // Followers of followers
    OPTIONAL MATCH (user)<-[:FOLLOWS]-(follower:User)-[:FOLLOWS]->(potential_follow)
    WITH user, potential_follow, common_follows_count, COUNT(DISTINCT follower) AS follower_of_follower_count
    // Interactions (likes, reposts, bookmarks, etc.)
    OPTIONAL MATCH (user)-[interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(post:Post)<-[:POSTED]-(potential_follow)
    OPTIONAL MATCH (user)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(post:Post)<-[:POSTED]-(potential_follow)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, COUNT(DISTINCT interaction) + COUNT(DISTINCT bookmark) AS interaction_count
    // Dating interactions
    OPTIONAL MATCH (user)-[swipe_right:SWIPED_RIGHT]->(potential_follow)
    OPTIONAL MATCH (user)-[swipe_left:SWIPED_LEFT]->(potential_follow)
    OPTIONAL MATCH (potential_follow)-[swipe_right_on_user:SWIPED_RIGHT]->(user)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count,
        COUNT(DISTINCT swipe_right) AS swiped_right_count,
        COUNT(DISTINCT swipe_left) AS swiped_left_count,
        COUNT(DISTINCT swipe_right_on_user) AS swiped_right_on_user_count
    // Location similarity (profile and recent)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
        CASE
            WHEN user.profile_location IS NOT NULL AND potential_follow.profile_location IS NOT NULL
                THEN point.distance(point({latitude: user.profile_location[0], longitude: user.profile_location[1]}), point({latitude: potential_follow.profile_location[0], longitude: potential_follow.profile_location[1]}))
            ELSE NULL
        END AS profile_distance,
        CASE
            WHEN user.recent_location IS NOT NULL AND potential_follow.recent_location IS NOT NULL
                THEN point.distance(point({latitude: user.recent_location[0], longitude: user.recent_location[1]}), point({latitude: potential_follow.recent_location[0], longitude: potential_follow.recent_location[1]}))
            ELSE NULL
        END AS recent_distance
    // Age similarity
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count, profile_distance, recent_distance, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
        CASE
            WHEN user.birth_datetime_utc IS NOT NULL AND potential_follow.birth_datetime_utc IS NOT NULL
                THEN abs(duration.between(date(user.birth_datetime_utc), date(potential_follow.birth_datetime_utc)).years)
            ELSE NULL
        END AS age_difference
    // Attended same school
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(potential_follow)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count, profile_distance, recent_distance, age_difference, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
        COUNT(DISTINCT school) AS common_school_count
    // Member of same organization
    OPTIONAL MATCH (user)-[:MEMBER_OF]->(organization:Organization)<-[:MEMBER_OF]-(potential_follow)
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count, profile_distance, recent_distance, age_difference, common_school_count, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
        COUNT(DISTINCT organization) AS common_organization_count
    // Calculate weighted score
    WITH user, potential_follow, common_follows_count, follower_of_follower_count, interaction_count, profile_distance, recent_distance, age_difference, common_school_count, common_organization_count, swiped_right_count, swiped_left_count, swiped_right_on_user_count,
        common_follows_count * 4 + follower_of_follower_count * 3 + interaction_count * 5 + common_organization_count * 2 +
        CASE
            WHEN profile_distance IS NOT NULL THEN 2 * EXP(-profile_distance / 1000)
            ELSE 0
        END +
        CASE
            WHEN recent_distance IS NOT NULL THEN 2 * EXP(-recent_distance / 1000)
            ELSE 0
        END +
        CASE
            WHEN age_difference IS NOT NULL THEN 2 * EXP(-age_difference / 10)
            ELSE 0
        END +
        common_school_count * 3 +
        swiped_right_count * 5 +
        swiped_right_on_user_count * 5 -
        swiped_left_count * 10
    AS score
    RETURN potential_follow.user_id AS recommended_user_id, potential_follow.username AS recommended_username, potential_follow.display_name AS recommended_display_name, potential_follow.profile_photo AS recommended_profile_photo, potential_follow.created_at AS recommended_created_at, score
    ORDER BY score DESC
    LIMIT 20
    """  # noqa: E501
    async with driver.session() as session:
        result = await session.run(query, {"user_id": verified_user.user_id})
        records = await result.data()
        recommendations = [
            SimpleUserResponse(
                user_id=record["recommended_user_id"],
                username=record["recommended_username"],
                display_name=record["recommended_display_name"],
                profile_photo=record.get("recommended_profile_photo"),
                created_at=datetime.fromisoformat(record["recommended_created_at"]),
            )
            for record in records
        ]
    return GetFollowRecommendationsResponse(recommendations=recommendations)


"--------------- ASTROLOGY -----------------"


class AstrologyCompatibilityDetails(BaseModel):
    """Represents the compatibility details for an astrology profile."""

    description: str
    score: float


class AstrologyCompatibility(BaseModel):
    """Represents the compatibility of two astrology profiles."""

    sun: AstrologyCompatibilityDetails
    moon: AstrologyCompatibilityDetails
    ascendant: AstrologyCompatibilityDetails
    mercury: AstrologyCompatibilityDetails
    venus: AstrologyCompatibilityDetails
    mars: AstrologyCompatibilityDetails
    jupiter: AstrologyCompatibilityDetails
    saturn: AstrologyCompatibilityDetails
    uranus: AstrologyCompatibilityDetails
    neptune: AstrologyCompatibilityDetails
    pluto: AstrologyCompatibilityDetails


class AstrologySign(BaseModel):
    """Represents the details of a single sign in the JSON file."""

    traits: list[str]
    description: str
    compatibility: AstrologyCompatibility


class AstrologySigns(BaseModel):
    """Represents the details of all signs in the JSON file."""

    aries: AstrologySign
    taurus: AstrologySign
    gemini: AstrologySign
    cancer: AstrologySign
    leo: AstrologySign
    virgo: AstrologySign
    libra: AstrologySign
    scorpio: AstrologySign
    sagittarius: AstrologySign
    capricorn: AstrologySign
    aquarius: AstrologySign
    pisces: AstrologySign


class AstrologyBody(BaseModel):
    """Represents the details of a single astrology body in the JSON file."""

    description: str
    themes: list[str]
    signs: AstrologySigns


class AstrologyData(BaseModel):
    """Represents the details of all astrology bodies in the JSON file."""

    sun: AstrologyBody
    moon: AstrologyBody
    ascendant: AstrologyBody
    mercury: AstrologyBody
    venus: AstrologyBody
    mars: AstrologyBody
    jupiter: AstrologyBody
    saturn: AstrologyBody
    uranus: AstrologyBody
    neptune: AstrologyBody
    pluto: AstrologyBody


def load_astrology_data() -> AstrologyData:
    """Load the astrology data from the JSON file."""
    with Path("new_zodiac_data.json").open() as f:
        contents = f.read()
    return AstrologyData(**json.loads(contents))


astrology_data = load_astrology_data()


def get_timezone_for_user(latitude: float, longitude: float) -> pytz.BaseTzInfo:
    """Get the timezone for a given latitude and longitude.

    Args:
        latitude (float): The latitude of the user.
        longitude (float): The longitude of the user.

    Returns:
        pytz.BaseTzInfo: The timezone for the given latitude and longitude.
    """
    tf = TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if not isinstance(timezone_str, str):
        error_message = "Timezone could not be determined."
        raise TypeError(error_message) from None
    return pytz.timezone(timezone_str)


def local_to_utc(
    datetime_of_user: datetime,
    lat: float,
    lon: float,
) -> datetime:
    """Convert a local datetime to UTC.

    Args:
        datetime_of_user (datetime.datetime): The local datetime to convert.
        lat (float): The latitude of the user.
        lon (float): The longitude of the user.

    Returns:
        datetime.datetime: The converted UTC datetime.
    """
    timezone = get_timezone_for_user(lat, lon)
    local_dt = datetime_of_user.astimezone(timezone)
    return local_dt.astimezone(pytz.utc)


def calculate_julian_day(utc_datetime: datetime) -> float:
    """Calculate the Julian day for a given UTC datetime.

    Args:
        utc_datetime (datetime): The UTC datetime.

    Returns:
        float: The Julian day.
    """
    try:
        return julday(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_datetime.hour + utc_datetime.minute / 60.0 + utc_datetime.second / 3600.0,
            SE_GREG_CAL,
        )

    except ValueError as e:
        raise ValueError(
            "An error occurred while calculating the Julian day: " + str(e),
        ) from e


HOUSE_SYSTEMS = {
    "Porphyry": b"O",
    "Placidus": b"P",
    "Koch": b"K",
    "Regiomontanus": b"R",
    "Campanus": b"C",
    "Equal": b"E",
    "Vehlow": b"V",
    "Whole Sign": b"W",
}

BODIES: dict[str, int] = {
    "Sun": SUN,
    "Moon": MOON,
    "Mercury": MERCURY,
    "Venus": VENUS,
    "Mars": MARS,
    "Jupiter": JUPITER,
    "Saturn": SATURN,
    "Uranus": URANUS,
    "Neptune": NEPTUNE,
    "Pluto": PLUTO,
}


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def calculate_body_positions(julian_day: float) -> dict[str, float]:
    """Calculate the positions of the celestial bodies.

    Args:
        julian_day (float): The Julian day.

    Returns:
        dict[str, float]: The positions of the celestial bodies.
    """
    positions: dict[str, float] = {}
    flags: int = FLG_SWIEPH + FLG_SPEED
    for body_name, body_id in BODIES.items():
        position, _ = cast(tuple[tuple[float], int], calc(julian_day, body_id, flags))
        positions[body_name] = position[0]
    return positions


def assign_houses_to_bodies(
    static_houses: list[float],
    body_houses: dict[str, int],
    positions: dict[str, float],
) -> dict[str, int]:
    """Assign houses to the celestial bodies.

    Args:
        static_houses (list[float]): The static houses.
        body_houses (dict[str, int]): The body houses.
        positions (dict[str, float]): The positions of the celestial bodies.

    Returns:
        dict[str, int]: The body houses.
    """
    for body_name, body_longitude in positions.items():
        assigned = False
        for i in range(len(static_houses) - 1):
            if static_houses[i] <= body_longitude < static_houses[i + 1]:
                body_houses[body_name] = i + 1
                assigned = True
            elif static_houses[i] > static_houses[i + 1]:
                if (body_longitude >= static_houses[i]) or (body_longitude < static_houses[i + 1]):
                    body_houses[body_name] = i + 1
                    assigned = True
            if not assigned:
                logger.warning(
                    "Could not assign house for %s at longitude %f",
                    body_name,
                    body_longitude,
                )
                body_houses[body_name] = 0  # Or handle as needed
    return body_houses


def get_sign_for_position(position: float) -> str:
    """Get the sign for a given position.

    Args:
        position (float): The position.

    Returns:
        str: The sign.
    """
    return SIGNS[int(position / 30)]


def assign_signs_to_bodies(
    positions: dict[str, float],
    body_signs: dict[str, str],
) -> dict[str, str]:
    """Assign signs to the celestial bodies.

    Args:
        positions (dict[str, float]): The positions of the celestial bodies.
        body_signs (dict[str, str]): The body signs.
    """
    for body_name, body_longitude in positions.items():
        body_signs[body_name] = get_sign_for_position(body_longitude)
    return body_signs


# Constants for house systems
house_systems = {
    "A": "A",  # Equal (Ascendant)
    "E": "E",  # Equal (MC)
    "C": "C",  # Campanus
    "K": "K",  # Koch
    "O": "O",  # Porphyry
    "R": "R",  # Regiomontanus
    "T": "T",  # Topocentric
    "V": "V",  # Vehlow Equal
    "W": "W",  # Whole Sign
    "X": "X",  # Axial Rotation System/ Meridian
    "H": "H",  # Horizon/ Azimuthal
    "G": "G",  # Gauquelin Sector
    "M": "M",  # Morinus
    "P": "P",  # Placidus
    "B": "B",  # Alcabitius
    "Q": "Q",  # Carter Polarity/ Dynamic Equal
    "Z": "Z",  # APC Houses
}


def calculate_houses(julian_day: float, lat: float, long: float, house_system: str) -> tuple[list[float], list[float]]:
    hsys = house_systems.get(house_system, "O")  # Default to Porphyry
    try:
        cusps, ascmc = houses(julian_day, lat, long, hsys)
        return cusps, ascmc
    except Exception as e:
        print(f"Error calculating houses: {e}")
        return ([], [])


class AstrologyChartCreationRequest(BaseModel):
    """Request model for creating an astrology chart."""

    birth_datetime: datetime
    latitude: float
    longitude: float


class UserAstrology(BaseModel):
    """Represents a user's astrology (simple)."""

    birth_datetime_utc: datetime | None = None
    birth_location: tuple[float, float] | None = None
    sun: str
    moon: str
    ascendant: str
    mercury: str
    venus: str
    mars: str
    jupiter: str
    saturn: str
    uranus: str
    neptune: str
    pluto: str


class AstrologyBodyDetails(BaseModel):
    """Represents the details of an as astrology body."""

    body_description: str
    body_themes: list[str]
    sign: str
    sign_description: str
    sign_traits: list[str]


class AstrologyDetailsSingleUser(BaseModel):
    """Represents the details of an astrology profile for a single user."""

    sun: AstrologyBodyDetails
    moon: AstrologyBodyDetails
    ascendant: AstrologyBodyDetails
    mercury: AstrologyBodyDetails
    venus: AstrologyBodyDetails
    mars: AstrologyBodyDetails
    jupiter: AstrologyBodyDetails
    saturn: AstrologyBodyDetails
    uranus: AstrologyBodyDetails
    neptune: AstrologyBodyDetails
    pluto: AstrologyBodyDetails


class AstrologyDetailsComparedDetails(BaseModel):
    """Represents the details of a comparison between two astrology profiles for a single body."""

    body_description: str
    body_themes: list[str]
    requesting_user_sign: str
    target_user_sign: str
    description: str
    score: float


class AstrologyDetailsCompared(BaseModel):
    """Represents the overall comparison between two astrology profiles."""

    sun: AstrologyDetailsComparedDetails
    moon: AstrologyDetailsComparedDetails
    ascendant: AstrologyDetailsComparedDetails
    mercury: AstrologyDetailsComparedDetails
    venus: AstrologyDetailsComparedDetails
    mars: AstrologyDetailsComparedDetails
    jupiter: AstrologyDetailsComparedDetails
    saturn: AstrologyDetailsComparedDetails
    uranus: AstrologyDetailsComparedDetails
    neptune: AstrologyDetailsComparedDetails
    pluto: AstrologyDetailsComparedDetails
    total_score: float


def get_astrology_details_for_body_single_user(
    celestial_body: str,
    zodiac_sign: str,
) -> AstrologyBodyDetails:
    """Get the details for a single astrology body for a single user.

    Args:
        celestial_body (str): The celestial body.
        zodiac_sign (str): The zodiac sign.

    Returns:
        AstrologyBodyDetails: The details for the astrology body.
    """
    celestial_body_data = astrology_data.__getattribute__(celestial_body)
    body_themes = celestial_body_data.__getattribute__.themes
    body_description = celestial_body_data.__getattribute__.description
    sign_for_body = celestial_body_data.__getattribute__(zodiac_sign)
    sign_description = sign_for_body.description
    sign_traits_for_body = sign_for_body.traits
    return AstrologyBodyDetails(
        body_description=body_description,
        body_themes=body_themes,
        sign=zodiac_sign,
        sign_description=sign_description,
        sign_traits=sign_traits_for_body,
    )


def get_astrology_details_for_comparison(
    celestial_body: str,
    requesting_user_sign: str,
    target_user_sign: str,
) -> AstrologyDetailsComparedDetails:
    """Get the details for comparing two astrology profiles for a single body.

    Args:
        celestial_body (str): The celestial body.
        requesting_user_sign (str): The sign of the requesting user.
        target_user_sign (str): The sign of the target user.

    Returns:
        AstrologyDetailsComparedDetails: The details for comparing two astrology
            profiles for a single body.
    """
    celestial_body_data = astrology_data.__getattribute__(celestial_body)
    requesting_user_body_details = celestial_body_data.__getattribute__(
        requesting_user_sign,
    )
    compatibility_data = requesting_user_body_details.compatibility.__getattribute__(
        target_user_sign,
    )
    celestial_body_description = celestial_body_data.description
    celestial_body_themes = celestial_body_data.themes
    compatibility_description = compatibility_data.description
    compatibility_score = compatibility_data.score
    return AstrologyDetailsComparedDetails(
        body_description=celestial_body_description,
        body_themes=celestial_body_themes,
        requesting_user_sign=requesting_user_sign,
        target_user_sign=target_user_sign,
        description=compatibility_description,
        score=compatibility_score,
    )


@router.get("/api/astrology/{user_id}", response_model=AstrologyDetailsSingleUser)
async def get_astrology_profile_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> AstrologyDetailsSingleUser:
    """Get the details for a single astrology body for a single user.

    Args:
        user_id (str): The ID of the user.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        AstrologyDetailsSingleUser: The details for the astrology body.
    """
    async with driver.session() as session:
        query = """
        MATCH (user:User {user_id: $user_id}))
        MATCH (requester:User {user_id: $requester_id})
        OPTIONAL MATCH (user)-[:BLOCKS]-(requester)
        WITH user, COUNT(DISTINCT user) AS block_count
        WHERE block_count = 0
        RETURN user.sun AS sun,
            user.moon AS moon,
            user.ascendant AS ascendant,
            user.mercury AS mercury,
            user.venus AS venus,
            user.mars AS mars,
            user.jupiter AS jupiter,
            user.saturn AS saturn,
            user.uranus AS uranus,
            user.neptune AS neptune,
            user.pluto AS pluto,
            user.birth_datetime_utc AS birth_datetime_utc,
            user.birth_location AS birth_location
        """
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail="User or astrology details not found.",
            )

        sun = get_astrology_details_for_body_single_user("sun", record["sun"])
        moon = get_astrology_details_for_body_single_user("moon", record["moon"])
        ascendant = get_astrology_details_for_body_single_user(
            "ascendant",
            record["ascendant"],
        )
        mercury = get_astrology_details_for_body_single_user(
            "mercury",
            record["mercury"],
        )
        venus = get_astrology_details_for_body_single_user("venus", record["venus"])
        mars = get_astrology_details_for_body_single_user("mars", record["mars"])
        jupiter = get_astrology_details_for_body_single_user(
            "jupiter",
            record["jupiter"],
        )
        saturn = get_astrology_details_for_body_single_user("saturn", record["saturn"])
        uranus = get_astrology_details_for_body_single_user("uranus", record["uranus"])
        neptune = get_astrology_details_for_body_single_user(
            "neptune",
            record["neptune"],
        )
        pluto = get_astrology_details_for_body_single_user("pluto", record["pluto"])

        return AstrologyDetailsSingleUser(
            sun=sun,
            moon=moon,
            ascendant=ascendant,
            mercury=mercury,
            venus=venus,
            mars=mars,
            jupiter=jupiter,
            saturn=saturn,
            uranus=uranus,
            neptune=neptune,
            pluto=pluto,
        )


@router.post("/api/astrology", response_model=None)
async def create_astrology_chart_route(
    request: AstrologyChartCreationRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """Create an astrology chart for a user."""
    # Convert local birth times to UTC
    birth_datetime_utc = local_to_utc(
        request.birth_datetime,
        request.latitude,
        request.longitude,
    )

    # Calculate Julian day
    julian_day = calculate_julian_day(birth_datetime_utc)

    # Calculate body positions
    positions = calculate_body_positions(julian_day)

    # Assign signs to bodies
    body_signs: dict[str, str] = {}
    body_signs = assign_signs_to_bodies(positions, body_signs)

    # Add ascendant to body signs
    _, ascmc = calculate_houses(
        julian_day,
        request.latitude,
        request.longitude,
        "O",
    )
    body_signs["ascendant"] = get_sign_for_position(
        ascmc[0],
    )

    async with driver.session() as session:
        query = """
        MATCH (user:User {user_id: $user_id})
        SET user.birth_datetime_utc = $birth_datetime_utc,
            user.birth_location = point({latitude: $latitude, longitude: $longitude}),
            user.sun = $sun,
            user.moon = $moon,
            user.ascendant = $ascendant,
            user.mercury = $mercury,
            user.venus = $venus,
            user.mars = $mars,
            user.jupiter = $jupiter,
            user.saturn = $saturn,
            user.uranus = $uranus,
            user.neptune = $neptune,
            user.pluto = $pluto
        """
        await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "birth_datetime_utc": birth_datetime_utc,
                "latitude": request.latitude,
                "longitude": request.longitude,
                "sun": body_signs["Sun"],
                "moon": body_signs["Moon"],
                "ascendant": body_signs["ascendant"],
                "mercury": body_signs["Mercury"],
                "venus": body_signs["Venus"],
                "mars": body_signs["Mars"],
                "jupiter": body_signs["Jupiter"],
                "saturn": body_signs["Saturn"],
                "uranus": body_signs["Uranus"],
                "neptune": body_signs["Neptune"],
                "pluto": body_signs["Pluto"],
            },
        )


@router.get("/api/astrology/compare/{user_id}", response_model=AstrologyDetailsCompared)
async def compare_astrology_route(
    user_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> AstrologyDetailsCompared:
    """Get the details for comparing astrology profiles between two users.

    Args:
        user_id (str): The ID of the user.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        AstrologyDetailsCompared: The details for comparing astrology profiles.
    """
    query = """
        MATCH (user:User {user_id: $user_id}))
        MATCH (requester:User {user_id: $requester_id})
        OPTIONAL MATCH (user)-[:BLOCKS]-(requester)
        WITH user, COUNT(DISTINCT user) AS block_count
        WHERE block_count = 0
        RETURN user.sun AS sun,
            user.moon AS moon,
            user.ascendant AS ascendant,
            user.mercury AS mercury,
            user.venus AS venus,
            user.mars AS mars,
            user.jupiter AS jupiter,
            user.saturn AS saturn,
            user.uranus AS uranus,
            user.neptune AS neptune,
            user.pluto AS pluto,
            requester.sun AS requester_sun,
            requester.moon AS requester_moon,
            requester.ascendant AS requester_ascendant,
            requester.mercury AS requester_mercury,
            requester.venus AS requester_venus,
            requester.mars AS requester_mars,
            requester.jupiter AS requester_jupiter,
            requester.saturn AS requester_saturn,
            requester.uranus AS requester_uranus,
            requester.neptune AS requester_neptune,
            requester.pluto AS requester_pluto,
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=404,
                detail="User or astrology details not found.",
            )
        sun = get_astrology_details_for_comparison(
            "sun",
            record["requester_sun"],
            record["sun"],
        )
        moon = get_astrology_details_for_comparison(
            "moon",
            record["requester_moon"],
            record["moon"],
        )
        ascendant = get_astrology_details_for_comparison(
            "ascendant",
            record["requester_ascendant"],
            record["ascendant"],
        )
        mercury = get_astrology_details_for_comparison(
            "mercury",
            record["requester_mercury"],
            record["mercury"],
        )
        venus = get_astrology_details_for_comparison(
            "venus",
            record["requester_venus"],
            record["venus"],
        )
        mars = get_astrology_details_for_comparison(
            "mars",
            record["requester_mars"],
            record["mars"],
        )
        jupiter = get_astrology_details_for_comparison(
            "jupiter",
            record["requester_jupiter"],
            record["jupiter"],
        )
        saturn = get_astrology_details_for_comparison(
            "saturn",
            record["requester_saturn"],
            record["saturn"],
        )
        uranus = get_astrology_details_for_comparison(
            "uranus",
            record["requester_uranus"],
            record["uranus"],
        )
        neptune = get_astrology_details_for_comparison(
            "neptune",
            record["requester_neptune"],
            record["neptune"],
        )
        pluto = get_astrology_details_for_comparison(
            "pluto",
            record["requester_pluto"],
            record["pluto"],
        )
        total_score = (
            (sun.score * 0.2)
            + (moon.score * 0.2)
            + (ascendant.score * 0.1)
            + (mercury.score * 0.1)
            + (venus.score * 0.1)
            + (mars.score * 0.1)
            + (jupiter.score * 0.05)
            + (saturn.score * 0.05)
            + (uranus.score * 0.033)
            + (neptune.score * 0.033)
            + (pluto.score * 0.033)
        )
        return AstrologyDetailsCompared(
            sun=sun,
            moon=moon,
            ascendant=ascendant,
            mercury=mercury,
            venus=venus,
            mars=mars,
            jupiter=jupiter,
            saturn=saturn,
            uranus=uranus,
            neptune=neptune,
            pluto=pluto,
            total_score=total_score,
        )


"--------------- FEED -----------------"


class PaginatedPostsResponse(BaseModel):
    posts: list[PostResponse]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/feed/general", response_model=PaginatedPostsResponse)
async def get_general_feed_route(
    cursor: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PaginatedPostsResponse:
    """Get the general feed for the user with pagination.

    Args:
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        skip (int, optional): The number of posts to skip. Defaults to 0.
        limit (int, optional): The number of posts to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        PaginatedPostsResponse: The list of posts in the user's feed.
    """
    cursor = cursor or datetime.now(UTC)
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (potential_post:Post)
    // Avoid posts that the user has already seen
    OPTIONAL MATCH (user)-[:VIEWED]->(potential_post)
    WITH user, potential_post, COUNT(DISTINCT potential_post) AS seen_count
    // Common interactions by people followed by the user
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WITH user, potential_post, seen_count, COUNT(DISTINCT interaction) + COUNT(DISTINCT bookmark) AS interaction_count
    // Posts by followed users
    OPTIONAL MATCH (user)-[:FOLLOWS]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, COUNT(DISTINCT poster) AS poster_count
    // Posts liked by similar users
    OPTIONAL MATCH (similar_user:User)-[similar_interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (similar_user)-[:BOOKMARKED]->(similar_bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WHERE (user)-[:LIKED|REPOSTED|QUOTED|REPLIED]->(post:Post)<-[:LIKED|REPOSTED|QUOTED|REPLIED]-(similar_user)
    OR (user)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(post:Post)<-[:BOOKMARKED]-(similar_user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, COUNT(DISTINCT similar_interaction) + COUNT(DISTINCT similar_bookmark) AS similar_interaction_count
    // Distance similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count,
        CASE
            WHEN user.profile_location IS NOT NULL AND potential_post.location IS NOT NULL
            THEN point.distance(point({latitude: user.profile_location[0], longitude: user.profile_location[1]}),
                                point({latitude: potential_post.location[0], longitude: potential_post.location[1]}))
            ELSE null
        END AS distance
    // Age similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance,
        CASE
            WHEN user.birth_datetime_utc IS NOT NULL AND potential_post.birth_datetime_utc IS NOT NULL
            THEN abs(duration.between(date(user.birth_datetime_utc), date(potential_post.birth_datetime_utc)).years)
            ELSE null
        END AS age_difference
    // Common schools
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference,
        COUNT(DISTINCT school) AS common_schools_count
    // Common organizations
    OPTIONAL MATCH (user)-[:MEMBER_OF]->(organization:Organization)<-[:MEMBER_OF]-(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count,
        COUNT(DISTINCT organization) AS common_organizations_count
    // Check for blocks and mutes
    OPTIONAL MATCH (potential_post)<-[:QUOTE_OF|REPLY_TO|REPOST_OF]-(original_post:Post)
    OPTIONAL MATCH (original_poster:User)-[:POSTED]->(original_post)
    OPTIONAL MATCH (user)-[:BLOCKS|MUTES]->(original_poster)
    OPTIONAL MATCH (original_poster)-[:BLOCKS|MUTES]->(user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count, common_organizations_count,
        COUNT(DISTINCT original_poster) AS block_mute_count
    // Check for swipe right
    OPTIONAL MATCH (user)-[:SWIPED_RIGHT]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count, common_organizations_count, block_mute_count,
        COUNT(DISTINCT poster) AS swipe_right_count
    // Calculate weighted score
    WITH potential_post,
        (CASE WHEN seen_count > 0 THEN -100 ELSE 0 END) +
        (CASE WHEN block_mute_count > 0 THEN -100 ELSE 0 END) +
        swipe_right_count * 10 + // Boost for swipe right posts
        interaction_count * 5 +
        poster_count * 3 +
        similar_interaction_count * 4 +
        (CASE WHEN distance IS NOT NULL THEN 2 * EXP(-distance / 1000) ELSE 0 END) +
        (CASE WHEN age_difference IS NOT NULL THEN 2 * EXP(-age_difference / 10) ELSE 0 END) +
        common_schools_count * 2 +
        common_organizations_count * 2 AS score
    WHERE score > 0
    RETURN potential_post.post_id AS post_id, potential_post.content AS content,
           potential_post.created_at AS created_at,
           potential_post.post_type AS post_type,
           potential_post.is_video AS is_video,
           potential_post.video_url AS video_url,
           potential_post.video_length AS video_length,
           potential_post.like_count AS like_count,
           potential_post.view_count AS view_count,
           potential_post.quote_count AS quote_count,
           potential_post.reply_count AS reply_count,
           potential_post.repost_count AS repost_count,
           potential_post.bookmark_count AS bookmark_count,
           potential_post.mentions AS mentions,
           potential_post.hashtags AS hashtags,
           potential_post.quoted_post AS quoted_post,
           potential_post.replied_post AS replied_post,
           potential_post.reposted_post AS reposted_post,
           potential_post.quoted_post_private AS quoted_post_private,
           potential_post.replied_post_private AS replied_post_private,
           potential_post.reposted_post_private AS reposted_post_private
    ORDER BY score DESC, potential_post.created_at DESC
    SKIP $skip
    LIMIT $limit
    """  # noqa: E501
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "cursor": cursor.isoformat(),
                "skip": skip,
                "limit": limit,
            },
        )
        response_data = await result.data()
        if not response_data:
            raise HTTPException(
                status_code=404,
                detail="User not found or access denied",
            )
        return PaginatedPostsResponse(
            posts=[PostResponse(**record) for record in response_data[:limit]],
            has_more=len(response_data) > limit,
            next_cursor=response_data[-1]["created_at"] if len(response_data) > limit else None,
        )


"--------------- POSTS -----------------"


class CreatePostRequest(BaseModel):
    """Request model for creating a new post."""

    content: str
    post_type: str = "general"
    is_video: bool = False
    video_url: str | None = None
    video_length: float | None = None
    attachments: list[str] | None = None
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    quoted_post_id: str | None = None
    replied_post_id: str | None = None
    reposted_post_id: str | None = None
    created_at: datetime = datetime.now(UTC)


@router.post("/api/post", response_model=WasSuccessfulResponse)
async def create_general_post_route(
    request: CreatePostRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Create a general post."""
    post_id = str(uuid4())
    post_data = request.model_dump()
    post_data["post_id"] = post_id

    concatenated_properties = f"{request.content} {" ".join(request.hashtags or [])} {" ".join(request.mentions or [])}"

    query = """
    WITH $concatenated_properties AS concatenated_properties
    CREATE (post:Post {
        post_id: $post_id,
        content: $content,
        created_at: $created_at,
        post_type: $post_type,
        is_video: $is_video,
        video_url: $video_url,
        video_length: $video_length,
        like_count: $like_count,
        view_count: $view_count,
        quote_count: $quote_count,
        reply_count: $reply_count,
        repost_count: $repost_count,
        bookmark_count: $bookmark_count,
        mentions: $mentions,
        hashtags: $hashtags,
    })
    WITH post, concatenated_properties
    CALL {
        WITH post, concatenated_properties
        CALL genai.vector.encode(concatenated_properties, 'AzureOpenAI', {
            token: $azure_token,
            resource: $azure_resource,
            deployment: $azure_deployment,
            dimensions: $embedding_dimensions,
        }) YIELD vector
        CALL db.create.setNodeVectorProperty(post, 'post_embeddings', vector)
    }
    RETURN post
    """
    async with driver.session() as session:
        await session.run(
            query,
            {
                "post_id": post_id,
                "content": post_data["content"],
                "created_at": post_data["created_at"].isoformat(),
                "post_type": post_data["post_type"],
                "is_video": post_data["is_video"],
                "video_url": post_data["video_url"],
                "video_length": post_data["video_length"],
                "attachments": post_data["attachments"],
                "mentions": post_data["mentions"],
                "hashtags": post_data["hashtags"],
                "concatenated_properties": concatenated_properties,
                "azure_token": settings_model.azure.openai.api_key,
                "azure_resource": settings_model.azure.openai.embedding.resource,
                "azure_deployment": settings_model.azure.openai.embedding.deployment_name,
                "embedding_dimensions": settings_model.azure.openai.embedding.dimensions,
            },
        )
    if request.quoted_post_id:
        query = """
            MATCH (p:Post {post_id: $post_id}), (quoted:Post {post_id: $quoted_post_id})
            CREATE (p)-[:QUOTED {created_at: $created_at}]->(quoted)
        """
        await session.run(
            query,
            {
                "post_id": post_id,
                "quoted_post_id": request.quoted_post_id,
                "created_at": request.created_at.isoformat(),
            },
        )
    if request.replied_post_id:
        query = """
            MATCH (p:Post {post_id: $post_id}), (replied:Post {post_id: $replied_post_id})
            CREATE (p)-[:REPLIED {created_at: $created_at}]->(replied)
        """
        await session.run(
            query,
            {
                "post_id": post_id,
                "replied_post_id": request.replied_post_id,
                "created_at": request.created_at.isoformat(),
            },
        )
    if request.reposted_post_id:
        query = """
            MATCH (p:Post {post_id: $post_id}), (reposted:Post {post_id: $reposted_post_id})
            CREATE (p)-[:REPOSTED {created_at: $created_at}]->(reposted)
        """
        await session.run(
            query,
            {
                "post_id": post_id,
                "reposted_post_id": request.reposted_post_id,
                "created_at": request.created_at.isoformat(),
            },
        )
    await session.run(
        """
        MATCH (p:Post {post_id: $post_id})
        MATCH (user:User {user_id: $user_id})
        CREATE (p)-[:POSTED {created_at: $created_at}]->(user)
        """,
        {
            "post_id": post_id,
            "user_id": verified_user.user_id,
            "created_at": request.created_at.isoformat(),
        },
    )
    return WasSuccessfulResponse(successful=True)


@router.get("/api/feed/video", response_model=PaginatedPostsResponse)
async def get_video_feed_route(
    cursor: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PaginatedPostsResponse:
    """Get the video feed for the user with pagination.

    Args:
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        skip (int, optional): The number of posts to skip. Defaults to 0.
        limit (int, optional): The number of posts to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user is not found or access is denied.

    Returns:
        PaginatedPostsResponse: The list of video posts in the user's feed.
    """
    cursor = cursor or datetime.now(UTC)
    user_id = verified_user.user_id
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (potential_post:Post)
    WHERE potential_post.is_video = true
    // Avoid posts that the user has already seen
    OPTIONAL MATCH (user)-[:VIEWED]->(potential_post)
    WITH user, potential_post, COUNT(DISTINCT potential_post) AS seen_count
    // Common interactions by people followed by the user
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(follower:User)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WITH user, potential_post, seen_count, COUNT(DISTINCT interaction) + COUNT(DISTINCT bookmark) AS interaction_count
    // Posts by followed users
    OPTIONAL MATCH (user)-[:FOLLOWS]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, COUNT(DISTINCT poster) AS poster_count
    // Posts liked by similar users
    OPTIONAL MATCH (similar_user:User)-[similar_interaction:LIKED|REPOSTED|QUOTED|REPLIED]->(potential_post)
    OPTIONAL MATCH (similar_user)-[:BOOKMARKED]->(similar_bookmark:Bookmark)-[:BOOKMARKS]->(potential_post)
    WHERE (user)-[:LIKED|REPOSTED|QUOTED|REPLIED]->(post:Post)<-[:LIKED|REPOSTED|QUOTED|REPLIED]-(similar_user)
    OR (user)-[:BOOKMARKED]->(bookmark:Bookmark)-[:BOOKMARKS]->(post:Post)<-[:BOOKMARKED]-(similar_user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, COUNT(DISTINCT similar_interaction) + COUNT(DISTINCT similar_bookmark) AS similar_interaction_count
    // Distance similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count,
        CASE
            WHEN user.profile_location IS NOT NULL AND potential_post.location IS NOT NULL
            THEN point.distance(point({latitude: user.profile_location[0], longitude: user.profile_location[1]}),
                                point({latitude: potential_post.location[0], longitude: potential_post.location[1]}))
            ELSE null
        END AS distance
    // Age similarity
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance,
        CASE
            WHEN user.birth_datetime_utc IS NOT NULL AND potential_post.birth_datetime_utc IS NOT NULL
            THEN abs(duration.between(date(user.birth_datetime_utc), date(potential_post.birth_datetime_utc)).years)
            ELSE null
        END AS age_difference
    // Common schools
    OPTIONAL MATCH (user)-[:ATTENDED]->(school:School)<-[:ATTENDED]-(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference,
        COUNT(DISTINCT school) AS common_schools_count
    // Common organizations
    OPTIONAL MATCH (user)-[:MEMBER_OF]->(organization:Organization)<-[:MEMBER_OF]-(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count,
        COUNT(DISTINCT organization) AS common_organizations_count
    // Check for blocks and mutes
    OPTIONAL MATCH (potential_post)<-[:QUOTE_OF|REPLY_TO|REPOST_OF]-(original_post:Post)
    OPTIONAL MATCH (original_poster:User)-[:POSTED]->(original_post)
    OPTIONAL MATCH (user)-[:BLOCKS|MUTES]->(original_poster)
    OPTIONAL MATCH (original_poster)-[:BLOCKS|MUTES]->(user)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count, common_organizations_count,
        COUNT(DISTINCT original_poster) AS block_mute_count
    // Check for swipe right
    OPTIONAL MATCH (user)-[:SWIPED_RIGHT]->(poster:User)-[:POSTED]->(potential_post)
    WITH user, potential_post, seen_count, interaction_count, poster_count, similar_interaction_count, distance, age_difference, common_schools_count, common_organizations_count, block_mute_count,
        COUNT(DISTINCT poster) AS swipe_right_count
    // Calculate weighted score
    WITH potential_post,
        (CASE WHEN seen_count > 0 THEN -100 ELSE 0 END) +
        (CASE WHEN block_mute_count > 0 THEN -100 ELSE 0 END) +
        swipe_right_count * 10 + // Boost for swipe right posts
        interaction_count * 5 +
        poster_count * 3 +
        similar_interaction_count * 4 +
        (CASE WHEN distance IS NOT NULL THEN 2 * EXP(-distance / 1000) ELSE 0 END) +
        (CASE WHEN age_difference IS NOT NULL THEN 2 * EXP(-age_difference / 10) ELSE 0 END) +
        common_schools_count * 2 +
        common_organizations_count * 2 AS score
    WHERE score > 0
    RETURN potential_post.post_id AS post_id, potential_post.content AS content,
           potential_post.created_at AS created_at,
           potential_post.post_type AS post_type,
           potential_post.is_video AS is_video,
           potential_post.video_url AS video_url,
           potential_post.video_length AS video_length,
           potential_post.like_count AS like_count,
           potential_post.view_count AS view_count,
           potential_post.quote_count AS quote_count,
           potential_post.reply_count AS reply_count,
           potential_post.repost_count AS repost_count,
           potential_post.bookmark_count AS bookmark_count,
           potential_post.mentions AS mentions,
           potential_post.hashtags AS hashtags,
           potential_post.quoted_post AS quoted_post,
           potential_post.replied_post AS replied_post,
           potential_post.reposted_post AS reposted_post,
           potential_post.quoted_post_private AS quoted_post_private,
           potential_post.replied_post_private AS replied_post_private,
           potential_post.reposted_post_private AS reposted_post_private
    ORDER BY score DESC, potential_post.created_at DESC
    SKIP $skip
    LIMIT $limit
    """  # noqa: E501
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "cursor": cursor.isoformat(),
                "skip": skip,
                "limit": limit,
            },
        )
        response_data = await result.data()
        if not response_data:
            raise HTTPException(
                status_code=404,
                detail="User not found or access denied",
            )
        return PaginatedPostsResponse(
            posts=[PostResponse(**record) for record in response_data[:limit]],
            has_more=len(response_data) > limit,
            next_cursor=response_data[-1]["created_at"] if len(response_data) > limit else None,
        )


@router.get("/api/post/{post_id}", response_model=PostResponse)
async def get_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostResponse:
    """Get a specific post.

    Args:
        post_id (str): The ID of the post to get.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        PostResponse: The post data.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    OPTIONAL MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (requester)-[:BLOCKS]-(author)
    WITH post, author, request, COUNT(DISTINCT author) AS block_count, COUNT(DISTINCT requester) AS follows_count
    WHERE block_count = 0 AND (NOT author.account_private OR follows_count > 0)

    OPTIONAL MATCH (post)-[:QUOTED]->(quoted_post:Post)
    OPTIONAL MATCH (post)-[:REPLIED]->(replied_post:Post)
    OPTIONAL MATCH (post)-[:REPOSTED]->(reposted_post:Post)

    OPTIONAL MATCH (quoted_post)<-[:POSTED]-(quoted_author:User)
    OPTIONAL MACTH (replied_post)<-[:POSTED]-(replied_author:User)
    OPTIONAL MATCH (reposted_post)<-[:POSTED]-(reposted_author:User)

    RETURN post {
        .post_id,
        .content,
        .created_at,
        .post_type,
        .is_video,
        .video_url,
        .video_length,
        .like_count,
        .view_count,
        .quote_count,
        .reply_count,
        .repost_count,
        .bookmark_count,
        .mentions,
        .hashtags,
        .quoted_post: CASE WHEN quoted_post IS NOT NULL AND (NOT quoted_author.account_private OR (requester)-[:FOLLOWS]->(quoted_author))
            THEN quoted_post {.*}
            ELSE NULL END,
        .replied_post: CASE WHEN replied_post IS NOT NULL AND (NOT replied_author.account_private OR (requester)-[:FOLLOWS]->(replied_author))
            THEN replied_post {.*}
            ELSE NULL END,
        .reposted_post: CASE WHEN reposted_post IS NOT NULL AND (NOT reposted_author.account_private OR (requester)-[:FOLLOWS]->(reposted_author))
            THEN reposted_post {.*}
            ELSE NULL END,
        quoted_post_private: CASE WHEN quoted_post IS NOT NULL AND quoted_author.account_private AND NOT (requester)-[:FOLLOWS]->(quoted_author)
            THEN true
            ELSE false END,
        replied_post_private: CASE WHEN replied_post IS NOT NULL AND replied_author.account_private AND NOT (requester)-[:FOLLOWS]->(replied_author)
            THEN true
            ELSE false END,
        reposted_post_private: CASE WHEN reposted_post IS NOT NULL AND reposted_author.account_private AND NOT (requester)-[:FOLLOWS]->(reposted_author)
            THEN true
            ELSE false END
    } AS post_data
    """  # noqa: E501
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )
        post_data = record["post_data"]
        return PostResponse(**post_data)


@router.delete("/api/post/{post_id}", response_model=WasSuccessfulResponse)
async def delete_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete a specific post.

    Args:
        post_id (str): The ID of the post to delete.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the deletion was successful.
    Raises:        HTTPException: If the post is not found or the user doesn't have permission to delete it.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})<-[:POSTED]-(author:User {user_id: $user_id})
    // Delete relationships
    OPTIONAL MATCH (post)-[r]->()
    DELETE r
    // Delete relationships pointing to this post
    OPTIONAL MATCH (post)<-[r]-()
    DELETE r
    // Handle bookmarks
    OPTIONAL MATCH (post)<-[:BOOKMARKS]-(bookmark:Bookmark)
    OPTIONAL MATCH (user)-[:BOOKMARKED]->(bookmark)
    DELETE bookmark
    // Delete the post
    DELETE post
    RETURN COUNT(post) AS deleted_count
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "user_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to delete it.",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- POST LIKES -----------------"


class PostLikesResponse(BaseModel):
    """Response model for getting a list of likes for a post."""

    likes: list[SimpleUserResponse]
    has_more: bool
    last_like_datetime: datetime | None = None


@router.get("/api/post/like/{post_id}", response_model=PostLikesResponse)
async def get_post_likes_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostLikesResponse:
    """Get likes for a specific post.

    Args:
        post_id (str): The ID of the post to get likes for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of likes to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to view it.

    Returns:
        PostLikesResponse: The response containing the list of likes.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (liker:User)-[like:LIKED]->(post)
    WHERE like.created_at < $cursor
        AND NOT (liker)-[:BLOCKS]-(requester)
    RETURN liker {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        created_at: like.created_at
    } AS like_data
    ORDER BY like.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.fetch(limit + 1)

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )

        likes = [SimpleUserResponse(**record["like_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["like_data"]["created_at"] if has_more else None

        return PostLikesResponse(
            likes=likes,
            has_more=has_more,
            last_like_datetime=next_cursor,
        )


class PostInteractionEvent(BaseModel):
    """Represents a post interaction event."""

    author_id: str
    score_increase: int


@router.post("/api/post/like/{post_id}", response_model=WasSuccessfulResponse)
async def like_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Like a specific post.

    Args:
        post_id (str): The ID of the post to like.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the like was successful.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to like it.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))
    AND NOT (requester)-[:POSTED]->(post)  // Ensure user is not liking their own post

    MERGE (requester)-[r:LIKED {created_at: $created_at}]->(post)
    ON CREATE SET post.like_count = COALESCE(post.like_count, 0) + 1
    RETURN r AS like, author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found, you don't have permission to like it, or you're trying to like your own post.",
            )
        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=1),
            topic="liked-post",
        )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/post/like/{post_id}", response_model=WasSuccessfulResponse)
async def unlike_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unlike a specific post.

    Args:
        post_id (str): The ID of the post to unlike.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to unlike it.

    Returns:
        WasSuccessfulResponse: A response indicating whether the unlike was successful.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    MATCH (requester)-[r:LIKED]->(post)
    DELETE r
    SET post.like_count = CASE WHEN post.like_count > 0 THEN post.like_count - 1 ELSE 0 END
    RETURN author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you haven't liked this post.",
            )
        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=-1),
            topic="remove-like-post",
        )
        return WasSuccessfulResponse(successful=True)


"--------------- POST REPOSTS -----------------"


class PostRepostsResponse(BaseModel):
    """Response model for getting a list of reposts for a post."""

    reposts: list[SimpleUserResponse]
    has_more: bool
    last_repost_datetime: datetime | None = None


@router.get("/api/post/repost/{post_id}", response_model=PostRepostsResponse)
async def get_post_reposts_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostRepostsResponse:
    """Get reposts for a specific post.

    Args:
        post_id (str): The ID of the post to get reposts for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of reposts to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to view it.

    Returns:
        PostRepostsResponse: The response containing the list of reposts.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (reposter:User)-[repost:REPOSTED]->(post)
    WHERE repost.created_at < $cursor
        AND NOT (reposter)-[:BLOCKS]-(requester)
    RETURN reposter {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        created_at: repost.created_at
    } AS repost_data
    ORDER BY repost.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.fetch(limit + 1)

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )

        reposts = [SimpleUserResponse(**record["repost_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["repost_data"]["created_at"] if has_more else None

        return PostRepostsResponse(
            reposts=reposts,
            has_more=has_more,
            last_repost_datetime=next_cursor,
        )


@router.post("/api/post/repost/{post_id}", response_model=WasSuccessfulResponse)
async def repost_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Repost a specific post.

    Args:
        post_id (str): The ID of the post to repost.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to repost it.

    Returns:
        WasSuccessfulResponse: A response indicating whether the repost was successful.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post is NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))
    AND NOT (requester)-[:POSTED]->(post)  // Ensure user is not reposting their own post

    MERGE (requester)-[r:REPOSTED {created_at: $created_at}]->(post)
    ON CREATE SET post.repost_count = COALESCE(post.repost_count, 0) + 1
    RETURN r AS repost, author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found, you don't have permission to repost it, or you're trying to repost your own post.",
            )
        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=2),
            topic="reposted-post",
        )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/post/repost/{post_id}", response_model=WasSuccessfulResponse)
async def unrepost_post_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Unrepost a specific post.

    Args:
        post_id (str): The ID of the post to unrepost.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to unrepost it.

    Returns:
        WasSuccessfulResponse: A response indicating whether the unrepost was successful.
    """
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    MATCH (requester)-[r:REPOSTED]->(post)
    DELETE r
    SET post.repost_count = CASE WHEN post.repost_count > 0 THEN post.repost_count - 1 ELSE 0 END
    RETURN author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to unrepost it.",
            )
        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=-2),
            topic="remove-repost-post",
        )
        return WasSuccessfulResponse(successful=True)


"--------------- POST QUOTES -----------------"


class PostQuotesResponse(BaseModel):
    """Response model for getting a list of quotes for a post."""

    quotes: list[SimpleUserResponse]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/post/quote/{post_id}", response_model=PostQuotesResponse)
async def get_post_quotes_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostQuotesResponse:
    """Get quotes for a specific post.

    TODO: Return the actual quote posts, not just the users.

    Args:
        post_id (str): The ID of the post to get quotes for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of quotes to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to view it.

    Returns:
        PostQuotesResponse: The response containing the list of quotes.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (quoter:User)-[quote:QUOTED]->(post)
    WHERE quote.created_at < $cursor
        AND NOT (quoter)-[:BLOCKS]-(requester)
    RETURN quoter {
        .user_id,
        .username,
        .display_name,
        .profile_photo,
        created_at: quote.created_at
    } AS quote_data
    ORDER BY quote.created_at DESC
    LIMIT $limit + 1
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.fetch(limit + 1)
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )
        quotes = [SimpleUserResponse(**record["quote_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["quote_data"]["created_at"] if has_more else None

        return PostQuotesResponse(
            quotes=quotes,
            has_more=has_more,
            next_cursor=next_cursor,
        )


class CreateQuotePostRequest(BaseModel):
    """Request model for creating a quote post."""

    post_id: str
    content: str
    post_type: str = "quote"
    is_video: bool = False
    video_url: str | None = None
    video_length: float | None = None
    attachments: list[str] | None = None
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    quoted_post_id: str
    replied_post_id: str | None = None
    reposted_post_id: str | None = None


@router.post("/api/post/quote/{post_id}", response_model=WasSuccessfulResponse)
async def create_post_quote_route(
    post_id: str,
    request: CreateQuotePostRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Create a quote post for a specific post.

    Args:
        post_id (str): The ID of the post being quoted.
        request (CreateQuotePostRequest): The data for the new quote post.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the quote post was created successfully.

    Raises:
        HTTPException: If the original post is not found or the user doesn't have permission to view it.
    """
    new_post_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    concatenated_properties = f"{request.content} {" ".join(request.hashtags or [])} {" ".join(request.mentions or [])}"

    query = """
    MATCH (original_post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (original_post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH original_post, requester, author
    WHERE original_post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    // Create the new quote post
    CREATE (new_post:Post {
        post_id: $new_post_id,
        content: $content,
        created_at: $created_at,
        post_type: 'quote',
        attachments: $attachments,
        mentions: $mentions,
        hashtags: $hashtags,
        like_count: 0,
        view_count: 0,
        quote_count: 0,
        reply_count: 0,
        repost_count: 0,
        bookmark_count: 0
    })

    // Create the POSTED relationship
    CREATE (requester)-[:POSTED {created_at: $created_at}]->(new_post)

    // Create the QUOTED relationship
    CREATE (new_post)-[:QUOTED {created_at: $created_at}]->(original_post)

    // Update the quote count of the original post
    SET original_post.quote_count = COALESCE(original_post.quote_count, 0) + 1

    // Generate and attach AI embeddings
    WITH new_post, $concatenated_properties AS text
    CALL genai.vector.encode(text, 'AzureOpenAI', {
        token: $azure_token,
        resource: $azure_resource,
        deployment: $azure_deployment,
        dimensions: $embedding_dimensions
    }) YIELD vector
    CALL db.create.setNodeVectorProperty(new_post, 'post_embeddings', vector)

    RETURN new_post, author.user_id AS author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "new_post_id": new_post_id,
                "requester_id": verified_user.user_id,
                "content": request.content,
                "created_at": created_at,
                "attachments": request.attachments,
                "mentions": request.mentions,
                "hashtags": request.hashtags,
                "concatenated_properties": concatenated_properties,
                "azure_token": settings_model.azure.openai.api_key,
                "azure_resource": settings_model.azure.openai.embedding.resource,
                "azure_deployment": settings_model.azure.openai.embedding.deployment_name,
                "embedding_dimensions": settings_model.azure.openai.embedding.dimensions,
            },
        )
        record = await result.single()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote post could not be created.",
            )
        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=2),
            topic="quoted-post",
        )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/post/quote/{post_id}", response_model=WasSuccessfulResponse)
async def delete_post_quote_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete a quote post and all its associated relationships.

    Args:
        post_id (str): The ID of the quote post to delete.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the deletion was successful.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to delete it.
    """
    query = """
    MATCH (quote_post:Post {post_id: $post_id})<-[:POSTED]-(requester:User {user_id: $requester_id})
    WHERE quote_post.post_type = 'quote'
    OPTIONAL MATCH (quote_post)-[r:QUOTED]->(original_post:Post)
    // Delete all relationships to and from the quote post
    OPTIONAL MATCH (quote_post)-[rel_from:LIKED|REPOSTED|QUOTED|REPLIED]->()
    OPTIONAL MATCH ()-[rel_to:LIKED|REPOSTED|QUOTED|REPLIED]->(quote_post)
    // Handle bookmarks
    OPTIONAL MATCH (quote_post)<-[:BOOKMARKS]-(bookmark:Bookmark)
    OPTIONAL MATCH (user)-[:BOOKMARKED]->(bookmark)
    DELETE rel_from, rel_to, bookmark
    // Decrease counters on the original post
    WITH quote_post, original_post, r
    SET original_post.quote_count = CASE WHEN original_post.quote_count > 0 THEN original_post.quote_count - 1 ELSE 0 END
    // Delete the QUOTED relationship and the quote post itself
    DELETE r, quote_post
    RETURN count(quote_post) AS deleted_count, original_post.user_id AS original_author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote post not found or you don't have permission to delete it.",
            )
        original_author_id = record["original_author_id"]
        if original_author_id:
            await router.broker.publish(
                PostInteractionEvent(author_id=original_author_id, score_increase=-2),
                topic="removed-quote-post",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- POST REPLIES -----------------"


class PostRepliesResponse(BaseModel):
    """Response model for getting a list of replies for a post."""

    replies: list[PostResponse]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/post/reply/{post_id}", response_model=PostRepliesResponse)
async def get_post_replies_route(
    post_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PostRepliesResponse:
    """Get replies for a specific post.

    Args:
        post_id (str): The ID of the post to get replies for.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int): The number of replies to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the post is not found or the user doesn't have permission to view it.

    Returns:
        PostRepliesResponse: The response containing the list of replies.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH post, requester, author
    WHERE post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    MATCH (replier:User)-[:POSTED]->(reply:Post)-[r:REPLIED]->(post)
    WHERE r.created_at < $cursor
        AND NOT (replier)-[:BLOCKS]-(requester)

    // Fetch related posts for replies (in case they are quotes or reposts)
    OPTIONAL MATCH (reply)-[:QUOTED]->(quoted_post:Post)
    OPTIONAL MATCH (reply)-[:REPOSTED]->(reposted_post:Post)

    // Check if the quoted or reposted posts are from private users not followed by the requesting user
    OPTIONAL MATCH (quoted_post)<-[:POSTED]-(quoted_author:User)
    OPTIONAL MATCH (reposted_post)<-[:POSTED]-(reposted_author:User)

    OPTIONAL MATCH (requester)-[:FOLLOWS]->(quoted_author)
    OPTIONAL MATCH (requester)-[:FOLLOWS]->(reposted_author)

    RETURN reply {
        .post_id,
        .content,
        .created_at,
        .post_type,
        .is_video,
        .video_url,
        .video_length,
        .like_count,
        .view_count,
        .quote_count,
        .reply_count,
        .repost_count,
        .bookmark_count,
        .mentions,
        .hashtags,
        quoted_post: CASE
            WHEN quoted_post IS NOT NULL AND (NOT quoted_author.account_private OR requester-[:FOLLOWS]->quoted_author)
            THEN quoted_post {.*}
            ELSE NULL
        END,
        reposted_post: CASE
            WHEN reposted_post IS NOT NULL AND (NOT reposted_author.account_private OR requester-[:FOLLOWS]->reposted_author)
            THEN reposted_post {.*}
            ELSE NULL
        END,
        quoted_post_private: CASE
            WHEN quoted_post IS NOT NULL AND quoted_author.account_private AND NOT requester-[:FOLLOWS]->quoted_author
            THEN true
            ELSE false
        END,
        reposted_post_private: CASE
            WHEN reposted_post IS NOT NULL AND reposted_author.account_private AND NOT requester-[:FOLLOWS]->reposted_author
            THEN true
            ELSE false
        END
    } AS reply_data
    ORDER BY r.created_at DESC
    LIMIT $limit + 1
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,  # Fetch one extra to determine if there are more results
            },
        )
        records = await result.fetch(limit + 1)

        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to view it.",
            )

        replies = [PostResponse(**record["reply_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["reply_data"]["created_at"] if has_more else None

        return PostRepliesResponse(
            replies=replies,
            has_more=has_more,
            next_cursor=next_cursor,
        )


class CreateReplyPostRequest(BaseModel):
    """Request model for creating a reply to a post."""

    post_id: str
    content: str
    post_type: str = "reply"
    is_video: bool = False
    video_url: str | None = None
    video_length: float | None = None
    attachments: list[str] | None = None
    mentions: list[str] | None = None
    hashtags: list[str] | None = None
    quoted_post_id: str | None = None
    replied_post_id: str
    reposted_post_id: str | None = None


@router.post("/api/post/reply/{post_id}", response_model=WasSuccessfulResponse)
async def create_post_reply_route(
    post_id: str,
    request: CreateReplyPostRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Create a reply post for a specific post.

    Args:
        post_id (str): The ID of the post being replied to.
        request (CreateReplyPostRequest): The data for the new reply post.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the reply post was created successfully.

    Raises:
        HTTPException: If the original post is not found or the user doesn't have permission to view it.
    """
    new_post_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()

    concatenated_properties = f"{request.content} {" ".join(request.hashtags or [])} {" ".join(request.mentions or [])}"

    query = """
    MATCH (original_post:Post {post_id: $post_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (original_post)<-[:POSTED]-(author:User)
    WHERE NOT (author)-[:BLOCKS]-(requester)
    WITH original_post, requester, author
    WHERE original_post IS NOT NULL AND (NOT author.account_private OR (requester)-[:FOLLOWS]->(author))

    // Create the new reply post
    CREATE (new_post:Post {
        post_id: $new_post_id,
        content: $content,
        created_at: $created_at,
        post_type: 'reply',
        is_video: $is_video,
        video_url: $video_url,
        video_length: $video_length,
        attachments: $attachments,
        mentions: $mentions,
        hashtags: $hashtags,
        like_count: 0,
        view_count: 0,
        quote_count: 0,
        reply_count: 0,
        repost_count: 0,
        bookmark_count: 0
    })

    // Create the POSTED relationship
    CREATE (requester)-[:POSTED {created_at: $created_at}]->(new_post)

    // Create the REPLIED relationship
    CREATE (new_post)-[:REPLIED {created_at: $created_at}]->(original_post)

    // Update the reply count of the original post
    SET original_post.reply_count = COALESCE(original_post.reply_count, 0) + 1

    // Generate and attach AI embeddings
    WITH new_post, $concatenated_properties AS text
    CALL genai.vector.encode(text, 'AzureOpenAI', {
        token: $azure_token,
        resource: $azure_resource,
        deployment: $azure_deployment,
        dimensions: $embedding_dimensions
    }) YIELD vector
    CALL db.create.setNodeVectorProperty(new_post, 'post_embeddings', vector)

    RETURN new_post, author.user_id AS author_id
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "new_post_id": new_post_id,
                "requester_id": verified_user.user_id,
                "content": request.content,
                "created_at": created_at,
                "is_video": request.is_video,
                "video_url": request.video_url,
                "video_length": request.video_length,
                "attachments": request.attachments,
                "mentions": request.mentions,
                "hashtags": request.hashtags,
                "concatenated_properties": concatenated_properties,
                "azure_token": settings_model.azure.openai.api_key,
                "azure_resource": settings_model.azure.openai.embedding.resource,
                "azure_deployment": settings_model.azure.openai.embedding.deployment_name,
                "embedding_dimensions": settings_model.azure.openai.embedding.dimensions,
            },
        )
        record = await result.single()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply post could not be created. The original post may not exist or you may not have permission to reply to it.",
            )

        author_id = record["author_id"]
        await router.broker.publish(
            PostInteractionEvent(author_id=author_id, score_increase=1),
            topic="replied-to-post",
        )

        return WasSuccessfulResponse(successful=True)


@router.delete("/api/post/reply/{post_id}", response_model=WasSuccessfulResponse)
async def delete_post_reply_route(
    post_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete a reply post and all its associated relationships.

    Args:
        post_id (str): The ID of the reply post to delete.
        verified_user (VerifiedUser): The verified user making the request.
    Returns:        WasSuccessfulResponse: A response indicating whether the deletion was successful.
    Raises:        HTTPException: If the post is not found or the user doesn't have permission to delete it.
    """
    query = """
    MATCH (reply_post:Post {post_id: $post_id})<-[:POSTED]-(requester:User {user_id: $requester_id})
    WHERE reply_post.post_type = 'reply'
    OPTIONAL MATCH (reply_post)-[r:REPLIED]->(original_post:Post)
    // Delete all relationships to and from the reply post
    OPTIONAL MATCH (reply_post)-[rel_from:LIKED|REPOSTED|QUOTED|REPLIED]->()
    OPTIONAL MATCH ()-[rel_to:LIKED|REPOSTED|QUOTED|REPLIED]->(reply_post)
    // Handle bookmarks
    OPTIONAL MATCH (reply_post)<-[:BOOKMARKS]-(bookmark:Bookmark)
    OPTIONAL MATCH (user)-[:BOOKMARKED]->(bookmark)
    DELETE rel_from, rel_to, bookmark
    // Delete the Bookmark nodes
    WITH reply_post, original_post, r, collect(bookmark) AS bookmarks
    FOREACH (b IN bookmarks | DETACH DELETE b)
    // Decrease counters on the original post
    WITH reply_post, original_post, r
    SET original_post.reply_count = CASE WHEN original_post.reply_count > 0 THEN original_post.reply_count - 1 ELSE 0 END
    // Delete the REPLIED relationship and the reply post itself
    DELETE r, reply_post
    RETURN count(reply_post) AS deleted_count, original_post.user_id AS original_author_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "post_id": post_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reply post not found or you don't have permission to delete it.",
            )
        original_author_id = record["original_author_id"]
        if original_author_id:
            await router.broker.publish(
                PostInteractionEvent(author_id=original_author_id, score_increase=-1),
                topic="removed-reply-post",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- BOOKMARKS -----------------"


class Bookmark(BaseModel):
    """Represents a bookmark."""

    bookmark_id: str
    post_id: str
    created_at: datetime


class BookmarkGroup(BaseModel):
    """Represents a bookmark group."""

    bookmark_group_id: str
    name: str
    photo_url: str
    description: str
    public: bool = False
    bookmark_count: int = 0
    updated_at: datetime
    created_at: datetime


class BookmarkGroupsResponse(BaseModel):
    """Represents a response for a list of the user's bookmark groups."""

    bookmark_groups: list[BookmarkGroup]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/bookmark/group/{user_id}", response_model=BookmarkGroupsResponse)
async def get_bookmark_groups_route(
    user_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at", regex="(created_at|updated_at)"),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BookmarkGroupsResponse:
    """Get the bookmark groups for a user.

    Args:
        user_id (str): The ID of the user.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int, optional): The number of bookmark groups to return. Defaults to 10.
        sort_by (str, optional): The field to sort the bookmark groups by. Defaults to "created_at".
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user or bookmark groups could not be retrieved.

    Returns:
        BookmarkGroupsResponse: The bookmark groups for the user.
    """
    cursor = cursor or datetime.now(UTC)
    sort_by_field = "created_at" if sort_by == "created_at" else "updated_at"
    query = """
    MATCH (target_user:User {user_id: $user_id})
    OPTIONAL MATCH (requester:User {user_id: $requester_id})-[:FOLLOWS]->(target_user)
    OPTIONAL MATCH (target_user)-[:BLOCKS]-(requester)
    WITH target__user, COUNT(requester) AS follows, COUNT(requester) > 0 AS blocked

    MATCH (target_user)-[:OWNS]->(group:BookmarkGroup)
    WHERE group.{sort_by} < $cursor
    AND (group.public = true OR target_user.user_id = $requester_id)
    RETURN group {
        .bookmark_group_id,
        .name,
        .photo_url,
        .description,
        .public,
        .bookmark_count,
        .updated_at,
        .created_at
    } AS bookmark_group
    ORDER BY group.{sort_by} DESC
    LIMIT $limit + 1
    """.replace("{sort_by}", sort_by_field)
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,
            },
        )
        records = await result.data()
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark groups not found.",
            )
        bookmark_groups = [BookmarkGroup(**record["bookmark_group"]) for record in records[:limit]]

        has_more = len(records) > limit
        if sort_by == "created_at":
            next_cursor = bookmark_groups[limit - 1].created_at if has_more else None
        else:
            next_cursor = bookmark_groups[limit - 1].updated_at if has_more else None
        return BookmarkGroupsResponse(
            bookmark_groups=bookmark_groups,
            has_more=has_more,
            next_cursor=next_cursor,
        )


class CheckBookmarkGroupExistsForUserResponse(BaseModel):
    """Response model for checking if a bookmark group exists for a user."""

    exists: bool


@router.get(
    "/api/bookmark/group/exists/{group_name}",
    response_model=CheckBookmarkGroupExistsForUserResponse,
)
async def check_bookmark_group_exists_for_user_route(
    group_name: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> CheckBookmarkGroupExistsForUserResponse:
    """Check if a bookmark group exists for a user.

    Args:
        group_name (str): The name of the bookmark group.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user or bookmark group could not be checked.

    Returns:
        CheckBookmarkGroupExistsForUserResponse: A response indicating whether the bookmark group exists for the user.
    """
    query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {name: $group_name})
    RETURN COUNT(group) > 0 AS exists
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "group_name": group_name,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark group not found.",
            )
        return CheckBookmarkGroupExistsForUserResponse(exists=record["exists"])


class CreateBookmarkGroupRequest(BaseModel):
    """Request model for creating a bookmark group."""

    name: str
    photo_url: str | None = None
    description: str | None = None
    public: bool = False


@router.post("/api/bookmark/group", response_model=BookmarkGroup)
async def create_bookmark_group_route(
    request: CreateBookmarkGroupRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> BookmarkGroup:
    """Create a bookmark group for a user.

    Args:
        request (CreateBookmarkGroupRequest): The data for the new bookmark group.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the user or bookmark group could not be created.

    Returns:
        BookmarkGroup: The created bookmark group.
    """
    query = """
    MATCH (user:User {user_id: $user_id})
    CREATE (user)-[:OWNS]->(bookmark_group:BookmarkGroup {
        bookmark_group_id: $bookmark_group_id,
        name: $name,
        photo_url: $photo_url,
        description: $description,
        public: $public,
        bookmark_count: 0,
        updated_at: $updated_at,
        created_at: $created_at
    })
    RETURN bookmark_group
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "name": request.name,
                "photo_url": request.photo_url,
                "description": request.description,
                "public": request.public,
                "updated_at": datetime.now(UTC).isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or bookmark group not found.",
            )
        return BookmarkGroup(**record["bookmark_group"])


class GetBookmarksForGroupRequest(BaseModel):
    """Request model for getting the bookmarks for a bookmark group."""

    bookmarks: list[PostResponse] | None = None
    has_more: bool | None = None
    next_cursor: datetime | None = None


@router.get(
    "/api/bookmark/group/{bookmark_group_id}",
    response_model=GetBookmarksForGroupRequest,
)
@router.get(
    "/api/bookmark/group/{bookmark_group_id}",
    response_model=GetBookmarksForGroupRequest,
)
async def get_bookmark_group_route(
    bookmark_group_id: str,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> GetBookmarksForGroupRequest:
    """Get the bookmarks for a bookmark group.

    Args:
        bookmark_group_id (str): The ID of the bookmark group.
        cursor (datetime, optional): The cursor for pagination. Defaults to None.
        limit (int, optional): The number of bookmarks to return. Defaults to 10.
        verified_user (VerifiedUser): The verified user making the request.

    Raises:
        HTTPException: If the bookmark group or bookmarks could not be retrieved.

    Returns:
        GetBookmarksForGroupRequest: The bookmarks for the bookmark group.
    """
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (bookmark_group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    OPTIONAL MATCH (bookmark_group)-[:CONTAINS]->(bookmark:Bookmark)-[:BOOKMARKS]->(post:Post)
    OPTIONAL MATCH (post)<-[:POSTED]-(author:User)
    OPTIONAL MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (requester)-[:FOLLOWS]->(author)
    OPTIONAL MATCH (requester)-[:BLOCKS]-(author)
    WITH bookmark_group, bookmark, post, author, requester, COUNT(DISTINCT author) AS follows_count, COUNT(DISTINCT requester) AS block_count
    WHERE bookmark.created_at < $cursor
    AND (bookmark_group.public = true OR bookmark_group.user_id = $requester_id)
    AND (author IS NULL OR (NOT author.account_private OR follows_count > 0))
    AND (block_count = 0)
    RETURN {
        bookmarks: collect({
            post_id: post.post_id,
            content: post.content,
            created_at: post.created_at,
            post_type: post.post_type,
            is_video: post.is_video,
            video_url: post.video_url,
            video_length: post.video_length,
            like_count: post.like_count,
            view_count: post.view_count,
            quote_count: post.quote_count,
            reply_count: post.reply_count,
            repost_count: post.repost_count,
            bookmark_count: post.bookmark_count,
            mentions: post.mentions,
            hashtags: post.hashtags,
            quoted_post: CASE
                WHEN post.quoted_post IS NOT NULL AND (NOT author.account_private OR follows_count > 0)
                THEN post.quoted_post
                ELSE NULL
            END,
            replied_post: CASE
                WHEN post.replied_post IS NOT NULL AND (NOT author.account_private OR follows_count > 0)
                THEN post.replied_post
                ELSE NULL
            END,
            reposted_post: CASE
                WHEN post.reposted_post IS NOT NULL AND (NOT author.account_private OR follows_count > 0)
                THEN post.reposted_post
                ELSE NULL
            END,
            quoted_post_private: CASE
                WHEN post.quoted_post IS NOT NULL AND author.account_private AND follows_count = 0
                THEN true
                ELSE false
            END,
            replied_post_private: CASE
                WHEN post.replied_post IS NOT NULL AND author.account_private AND follows_count = 0
                THEN true
                ELSE false
            END,
            reposted_post_private: CASE
                WHEN post.reposted_post IS NOT NULL AND author.account_private AND follows_count = 0
                THEN true
                ELSE false
            END
        })[0..$limit] AS bookmarks,
        has_more: size(collect(post)) > $limit,
        next_cursor: CASE
            WHEN size(collect(post)) > $limit THEN post.created_at
            ELSE NULL
        END
    } AS response_data
    ORDER BY post.created_at DESC
    LIMIT $limit + 1
    """  # noqa: E501
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "bookmark_group_id": bookmark_group_id,
                "requester_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit,
            },
        )
        response_data = await result.single()
        if not response_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark group or bookmarks not found.",
            )
        return GetBookmarksForGroupRequest(
            bookmarks=[PostResponse(**record) for record in response_data["bookmarks"]],
            has_more=response_data["has_more"],
            next_cursor=response_data["next_cursor"],
        )


class UpdateBookmarkGroupRequest(BaseModel):
    """Request model for updating a bookmark group."""

    name: str | None = None
    photo_url: str | None = None
    description: str | None = None
    public: bool | None = None


@router.put(
    "/api/bookmark/group/{bookmark_group_id}",
    response_model=WasSuccessfulResponse,
)
async def update_bookmark_group_route(
    bookmark_group_id: str,
    request: UpdateBookmarkGroupRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Update a bookmark group for a user."""
    # Construct the SET clause dynamically based on provided fields
    set_clauses: list[str] = []
    params = {
        "user_id": verified_user.user_id,
        "bookmark_group_id": bookmark_group_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    for field, value in request.model_dump(exclude_unset=True).items():
        set_clauses.append(f"group.{field} = ${field}")
        params[field] = value
    set_clause = ", ".join(set_clauses)

    query = cast(
        LiteralString,
        f"""
    MATCH (user:User {{user_id: $user_id}})-[:OWNS]->(group:BookmarkGroup {{bookmark_group_id: $bookmark_group_id}})
    SET {set_clause}, group.updated_at = $updated_at
    RETURN COUNT(group) > 0 AS updated
    """,
    )
    async with driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()
        if not record or not record["updated"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this bookmark group.",
            )
        return WasSuccessfulResponse(successful=True)


@router.delete(
    "/api/bookmark/group/{bookmark_group_id}",
    response_model=WasSuccessfulResponse,
)
async def delete_bookmark_group_route(
    bookmark_group_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete a bookmark group for a user."""
    query = """
    MATCH (user:User {user_id: $user_id})-[:OWNS]->(group:BookmarkGroup {bookmark_group_id: $bookmark_group_id})
    OPTIONAL MATCH (group)-[r:CONTAINS]->(bookmark:Bookmark)
    OPTIONAL MATCH (bookmark)-[b:BOOKMARKS]->(post:Post)
    DELETE r, b, bookmark, group
    RETURN COUNT(group) > 0 AS deleted
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "bookmark_group_id": bookmark_group_id,
            },
        )
        record = await result.single()
        if not record or not record["deleted"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this bookmark group.",
            )
        return WasSuccessfulResponse(successful=True)


class AddBookmarkRequest(BaseModel):
    """Request model for adding a bookmark to a bookmark group."""

    post_id: str
    group_id: str


@router.post("/api/bookmark", response_model=WasSuccessfulResponse)
async def add_bookmark_to_bookmark_group_route(
    request: AddBookmarkRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Add a bookmark to a bookmark group.

    Args:
        request (AddBookmarkRequest): The request containing the post ID and group ID.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the addition was successful.

    Raises:
        HTTPException: If the post or group is not found.
    """
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (post:Post {post_id: $post_id})
    MATCH (group:Group {group_id: $group_id})
    // Create a new Bookmark node
    CREATE (bookmark:Bookmark {bookmark_id: apoc.create.uuid(), created_at: datetime()})
    // Create relationships
    CREATE (user)-[:BOOKMARKED]->(bookmark)
    CREATE (bookmark)-[:BOOKMARKS]->(post)
    CREATE (group)-[:CONTAINS]->(bookmark)
    RETURN bookmark
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "post_id": request.post_id,
                "group_id": request.group_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post or group not found.",
            )
        return WasSuccessfulResponse(successful=True)


@router.delete("/api/bookmark/{bookmark_id}", response_model=WasSuccessfulResponse)
async def delete_bookmark_route(
    bookmark_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """Delete a bookmark.

    Args:
        bookmark_id (str): The ID of the bookmark to delete.
        verified_user (VerifiedUser): The verified user making the request.

    Returns:
        WasSuccessfulResponse: A response indicating whether the deletion was successful.

    Raises:
        HTTPException: If the bookmark is not found or the user doesn't have permission to delete it.
    """
    query = """
    MATCH (bookmark:Bookmark {bookmark_id: $bookmark_id})
    MATCH (user:User {user_id: $user_id})
    MATCH (bookmark)-[:BOOKMARKS]->(post:Post)
    OPTIONAL MATCH (bookmark)-[:BOOKMARKED]->(user)
    DELETE bookmark
    RETURN COUNT(bookmark) AS deleted_count
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "bookmark_id": bookmark_id,
                "user_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record or record["deleted_count"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found or you don't have permission to delete it.",
            )
        return WasSuccessfulResponse(successful=True)


"--------------- SEARCH -----------------"


class SearchQueryRequest(BaseModel):
    """Request model for searching for posts."""

    contains_all: list[str] | None = None
    contains_any: list[str] | None = None
    exclude: list[str] | None = None
    use_semantic_search: bool | None = False
    from_date: datetime | None = None
    to_date: datetime | None = None
    authors: list[str] | None = None
    exclude_authors: list[str] | None = None
    hashtags: list[str] | None = None
    mentioned_users: list[str] | None = None
    post_types: list[str] | None = None  # e.g., ["general", "repost", "quote", "video", "reply"]
    following_only: bool | None = False
    group_ids: list[str] | None = None


@router.post("/api/search/posts", response_model=PaginatedPostsResponse)
async def search_posts_route(
    search_query: SearchQueryRequest,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> PaginatedPostsResponse:
    cursor = cursor or datetime.now(UTC)

    # Start with a base query
    base_query = """
    MATCH (post:Post)
    WHERE post.created_at < $cursor
    """

    # Add conditions based on search parameters
    conditions: list[str] = []
    params: dict[str, Any] = {
        "cursor": cursor.isoformat(),
        "limit": limit,
        "user_id": verified_user.user_id,
    }

    if search_query.from_date:
        conditions.append("post.created_at >= $from_date")
        params["from_date"] = search_query.from_date.isoformat()

    if search_query.to_date:
        conditions.append("post.created_at <= $to_date")
        params["to_date"] = search_query.to_date.isoformat()

    if search_query.contains_all:
        conditions.append("ALL(keyword IN $contains_all WHERE post.content CONTAINS keyword)")
        params["contains_all"] = search_query.contains_all

    if search_query.contains_any:
        conditions.append("ANY(keyword IN $contains_any WHERE post.content CONTAINS keyword)")
        params["contains_any"] = search_query.contains_any

    if search_query.exclude:
        conditions.append("NONE(keyword IN $exclude WHERE post.content CONTAINS keyword)")
        params["exclude"] = search_query.exclude

    if search_query.authors:
        conditions.append("post.author_id IN $authors")
        params["authors"] = search_query.authors

    if search_query.exclude_authors:
        conditions.append("NOT post.author_id IN $exclude_authors")
        params["exclude_authors"] = search_query.exclude_authors

    if search_query.hashtags:
        conditions.append("ALL(hashtag IN $hashtags WHERE hashtag IN post.hashtags)")
        params["hashtags"] = search_query.hashtags

    if search_query.mentioned_users:
        conditions.append("ALL(mention IN $mentioned_users WHERE mention IN post.mentions)")
        params["mentioned_users"] = search_query.mentioned_users

    if search_query.post_types:
        conditions.append("post.post_type IN $post_types")
        params["post_types"] = search_query.post_types

    if search_query.following_only:
        conditions.append("(user)-[:FOLLOWS]->(post.author)")

    if search_query.group_ids:
        conditions.append("post.group_id IN $group_ids")
        params["group_ids"] = search_query.group_ids

    # Add privacy and blocking conditions
    conditions.extend([
        "NOT (user)-[:BLOCKS]->(post.author)",
        "NOT (post.author)-[:BLOCKS]->(user)",
        "NOT (user)-[:MUTES]->(post.author)",
        "NOT (post.author)-[:MUTES]->(user)",
        "(NOT post.author.account_private OR (user)-[:FOLLOWS]->(post.author))",
    ])

    # Combine all conditions
    if conditions:
        base_query += " AND " + " AND ".join(conditions)

    # Add ordering
    base_query += " RETURN post ORDER BY post.created_at DESC LIMIT $limit"
    literal_query = cast(LiteralString, base_query)
    async with driver.session() as session:
        result = await session.run(literal_query, params)
        records = await result.data()

        if search_query.use_semantic_search and records:
            # Perform semantic search on the initial results
            semantic_query = """
            UNWIND $posts AS post
            WITH post, post.content + " " +
                 coalesce(reduce(s = "", hashtag IN post.hashtags | s + " #" + hashtag), "") + " " +
                 coalesce(reduce(s = "", mention IN post.mentions | s + " @" + mention), "") AS concatenated_properties
            CALL genai.vector.encode(concatenated_properties, 'AzureOpenAI', {
                token: $azure_token,
                resource: $azure_resource,
                deployment: $azure_deployment
            }) YIELD vector AS embedding
            WITH post, embedding
            CALL db.index.vector.queryNodes('post-embeddings', $limit, embedding)
            YIELD node AS similarPost, score
            RETURN similarPost AS post
            ORDER BY score DESC, similarPost.created_at DESC
            LIMIT $limit
            """
            semantic_params = {
                "posts": records,
                "limit": limit,
                "azure_token": settings_model.azure.openai.api_key,
                "azure_resource": settings_model.azure.openai.embedding.resource,
                "azure_deployment": settings_model.azure.openai.embedding.deployment_name,
            }
            semantic_result = await session.run(semantic_query, semantic_params)
            records = await semantic_result.data()

        posts = [PostResponse(**record["post"]) for record in records]
        create_search_history_query = """
            CREATE (search:SearchHistory {
                search_id: $search_id,
                query: $query,
                timestamp: $timestamp,
                result_count: $result_count
            })
            WITH search
            MATCH (user:User {user_id: $user_id})
            CREATE (user)-[:PERFORMED]->(search)
        """
        search_history_params = {
            "search_id": str(uuid4()),
            "query": str(search_query),  # You might want to serialize this differently
            "timestamp": datetime.now(UTC).isoformat(),
            "result_count": len(posts),
            "user_id": verified_user.user_id,
        }

        await session.run(cast(LiteralString, create_search_history_query), search_history_params)

        return PaginatedPostsResponse(
            posts=posts[:limit],
            has_more=len(posts) > limit,
            next_cursor=posts[-1].created_at if len(posts) > limit else None,
        )


class SearchHistoryItem(BaseModel):
    search_id: str
    query: str
    timestamp: datetime
    result_count: int


class SearchHistoryResponse(BaseModel):
    searches: list[SearchHistoryItem]
    has_more: bool
    next_cursor: datetime | None = None


@router.get("/api/search/history", response_model=SearchHistoryResponse)
async def get_search_history_route(
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> SearchHistoryResponse:
    cursor = cursor or datetime.now(UTC)

    query = """
    MATCH (user:User {user_id: $user_id})-[:PERFORMED]->(search:SearchHistory)
    WHERE search.timestamp < $cursor
    RETURN search {
        .search_id,
        .query,
        .timestamp,
        .result_count
    } AS search_data
    ORDER BY search.timestamp DESC
    LIMIT $limit + 1
    """

    params = {
        "user_id": verified_user.user_id,
        "cursor": cursor.isoformat(),
        "limit": limit + 1,  # We fetch one extra to determine if there are more results
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        records = await result.data()

        searches = [SearchHistoryItem(**record["search_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit]["search_data"]["timestamp"] if has_more else None

        return SearchHistoryResponse(
            searches=searches,
            has_more=has_more,
            next_cursor=next_cursor,
        )


class DeleteSearchHistoryResponse(BaseModel):
    deleted_count: int
    message: str


@router.delete("/api/search/history", response_model=DeleteSearchHistoryResponse)
async def delete_search_history_route(
    verified_user: VerifiedUser = Depends(get_current_user),
) -> DeleteSearchHistoryResponse:
    query = """
    MATCH (user:User {user_id: $user_id})-[:PERFORMED]->(search:SearchHistory)
    WITH search, count(search) as count
    DETACH DELETE search
    RETURN count
    """

    params = {
        "user_id": verified_user.user_id,
    }

    async with driver.session() as session:
        try:
            result = await session.run(query, params)
            record = await result.single()

            if record and "count" in record:
                deleted_count = record["count"]
                return DeleteSearchHistoryResponse(
                    deleted_count=deleted_count,
                    message=f"Successfully deleted {deleted_count} search history entries.",
                )
            else:
                return DeleteSearchHistoryResponse(
                    deleted_count=0,
                    message="No search history entries found to delete.",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while deleting search history: {e!s}",
            )


class DeleteSearchHistoryItemResponse(BaseModel):
    deleted: bool
    message: str


@router.delete("/api/search/history/{search_id}", response_model=DeleteSearchHistoryItemResponse)
async def delete_search_history_item_route(
    search_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> DeleteSearchHistoryItemResponse:
    query = """
    MATCH (user:User {user_id: $user_id})-[:PERFORMED]->(search:SearchHistory {search_id: $search_id})
    WITH search
    DETACH DELETE search
    RETURN COUNT(search) AS deleted_count
    """

    params = {
        "user_id": verified_user.user_id,
        "search_id": search_id,
    }

    async with driver.session() as session:
        try:
            result = await session.run(cast(LiteralString, query), params)
            record = await result.single()

            if record and record["deleted_count"] > 0:
                return DeleteSearchHistoryItemResponse(
                    deleted=True,
                    message=f"Successfully deleted search history item with ID: {search_id}",
                )
            else:
                return DeleteSearchHistoryItemResponse(
                    deleted=False,
                    message=f"No search history item found with ID: {search_id}",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while deleting search history item: {e!s}",
            )


class UserSearchRequest(BaseModel):
    query: str
    only_show_following: bool = False


class UserSearchResponse(BaseModel):
    """Response model for searching for users."""

    users: list[SimpleUserResponse]
    has_more: bool
    next_cursor: datetime | None = None


@router.post("/api/search/users", response_model=UserSearchResponse)
async def search_users_route(
    search_query: UserSearchRequest,
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> UserSearchResponse:
    cursor = cursor or datetime.now(UTC)

    query = """
    // Generate embedding for the search query
    CALL genai.vector.encode($search_query, 'AzureOpenAI', {
        token: $azure_token,
        resource: $azure_resource,
        deployment: $azure_deployment,
        dimensions: $embedding_dimensions
    }) YIELD vector AS query_embedding

    // Perform vector search on users
    MATCH (user:User)
    WHERE user.user_id <> $current_user_id
      AND user.created_at < $cursor
      AND NOT (user)-[:BLOCKS]-(:User {user_id: $current_user_id})
      AND NOT (:User {user_id: $current_user_id})-[:BLOCKS]->(user)
      AND NOT (:User {user_id: $current_user_id})-[:MUTES]->(user)
    """

    if search_query.only_show_following:
        query += "AND (:User {user_id: $current_user_id})-[:FOLLOWS]->(user) "

    query += """
    WITH user, query_embedding
    CALL db.index.vector.queryNodes('user_embeddings', $limit + 1, query_embedding) YIELD node, score
    WHERE node = user
    RETURN user {
        .user_id,
        .profile_photo,
        .username,
        .display_name,
        .created_at
    } AS user_data, score
    ORDER BY score DESC, user.created_at DESC
    LIMIT $limit + 1
    """

    params = {
        "current_user_id": verified_user.user_id,
        "cursor": cursor.isoformat(),
        "limit": limit + 1,
        "search_query": search_query.query,
        "azure_token": settings_model.azure.openai.api_key,
        "azure_resource": settings_model.azure.openai.embedding.resource,
        "azure_deployment": settings_model.azure.openai.embedding.deployment_name,
        "embedding_dimensions": settings_model.azure.openai.embedding.dimensions,
    }

    async with driver.session() as session:
        result = await session.run(query, params)
        records = await result.data()

        if not records:
            return UserSearchResponse(users=[], has_more=False, next_cursor=None)

        users = [SimpleUserResponse(**record["user_data"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = records[limit - 1]["user_data"]["created_at"] if has_more else None

        return UserSearchResponse(
            users=users,
            has_more=has_more,
            next_cursor=next_cursor,
        )


"--------------- NOTIFICATIONS -----------------"


@router.get("/api/notifications", response_model=NotificationResponse)
async def get_notifications_route(
    cursor: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> NotificationResponse:
    cursor = cursor or datetime.now(UTC)
    query = """
    MATCH (user:User {user_id: $user_id})-[:RECEIVED]->(n:Notification)
    WHERE n.updated_at < $cursor
    WITH n
    ORDER BY n.updated_at DESC
    LIMIT $limit

    MATCH (action_user:User)-[:ACTED_ON]->(n)
    WITH n, action_user
    ORDER BY action_user.user_id
    LIMIT 2

    RETURN {
        notification_id: n.notification_id,
        notification_type: n.notification_type,
        reference_id: n.reference_id,
        content_preview: n.content_preview,
        action_users: collect({
            user_id: action_user.user_id,
            username: action_user.username,
            display_name: action_user.display_name,
            profile_photo: action_user.profile_photo
        }),
        action_count: count(action_user)
        is_read: n.is_read,
        updated_at: n.updated_at
    } AS notification
    ORDER BY n.updated_at DESC
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "cursor": cursor.isoformat(),
                "limit": limit + 1,
            },
        )
        records = await result.data()

        notifications = [NotificationGroup(**record["notification"]) for record in records[:limit]]
        has_more = len(records) > limit
        next_cursor = notifications[-1].updated_at if has_more else None

        return NotificationResponse(
            notifications=notifications,
            has_more=has_more,
            next_cursor=next_cursor,
        )


@router.post("/api/notification")
async def mark_notification_route():
    pass


"--------------- PREDICTIONS -----------------"


@router.get("/api/prediction")
async def get_predictions_route():
    pass


@router.post("/api/prediction")
async def create_prediction_route():
    pass


@router.delete("/api/prediction/{prediction_id}")
async def delete_prediction_route(prediction_id: str):
    pass


@router.get("/api/prediction/{prediction_id}")
async def get_prediction_details_route(prediction_id: str):
    pass


@router.post("/api/prediction/{prediction_id}")
async def create_prediction_answer_route(prediction_id: str):
    pass


"--------------- LEADERBOARDS -----------------"


@router.get("/api/leaderboards")
async def get_current_leaderboards_route():
    pass


@router.post("/api/leaderboards")
async def get_advanced_filtered_leaderboards_route():
    pass


@router.get("/api/leaderboards/likes")
async def get_current_likes_leaderboard_route():
    pass


@router.get("/api/leaderboards/reposts")
async def get_current_reposts_leaderboard_route():
    pass


@router.get("/api/leaderboards/prior/likes")
async def get_prior_likes_leaderboard_route():
    pass


@router.get("/api/leaderboards/prior/reposts")
async def get_prior_reposts_leaderboard_route():
    pass


"--------------- PERSONALITY -----------------"

question_mapping = {}
with Path("questions.json").open() as f:
    question_mapping_string = f.read()
    question_mapping = json.loads(question_mapping_string)


async def calculate_trait_scores(
    user_answers: dict[str, bool],
) -> dict[str, float]:
    """Calculate the trait scores for a user based on their answers and weights.

    Args:
        user_answers (dict[str, bool]): question_id key and bool value

    Returns:
        dict[str, float]: The trait scores for the user.

    Example:
        >>> await calculate_trait_scores(
        ...     {
        ...         "Do you ever make unnecessary and loud noises when
                        you're home alone?": True
        ...     },
        ...     {"Introversion/Extraversion": {"Thinking/Feeling": 1.0}},
        ... )
        {"Introversion/Extraversion": 0.0}
    """
    trait_scores: dict[str, dict[str, float]] = {}
    for question_id in user_answers:
        answer = user_answers[question_id]
        if question_id not in question_mapping:
            continue
        for trait in cast(
            dict[str, str | dict[str, float]],
            question_mapping[question_id],
        ):
            if trait == "question":
                continue
            if trait not in trait_scores:
                trait_scores[trait] = {
                    "cumulative_score": 0.0,
                    "count": 0,
                }
            if answer:
                trait_scores[trait]["cumulative_score"] += cast(
                    float,
                    question_mapping[question_id][trait]["presence_given_yes"],
                )
                trait_scores[trait]["count"] += 1
            else:
                trait_scores[trait]["cumulative_score"] += cast(
                    float,
                    question_mapping[question_id][trait]["presence_given_no"],
                )
                trait_scores[trait]["count"] += 1
    normalized_scores: dict[str, float] = {}
    for trait in trait_scores:
        trait_data = trait_scores[trait]
        if trait_data["count"] > 0:
            raw_score = trait_data["cumulative_score"] / trait_data["count"]
            weight = 4
            median_value = 0.5
            if raw_score > median_value:
                weighted_score = median_value + (raw_score - median_value) * weight
            else:
                weighted_score = median_value - (median_value - raw_score) * weight
            normalized_score = min(max(weighted_score, 0.0), 1.0)
        else:
            normalized_score: float = 0.0
        normalized_scores[trait] = float(normalized_score)
    return normalized_scores


# async def get_trait_scores_paired(
#     user1_id: str,
#     user2_id: str,
# ) -> tuple[dict[str, float], dict[str, float]]:
#     """Compare the trait scores for two users based on their answers and weights.

#     Args:
#         user1_id (str): The ID of the first user.
#         user2_id (str): The ID of the second user.

#     Returns:
#         tuple[dict[str, float], dict[str, float]]: The trait scores for the two users.
#     """
#     users_answers = await get_both_user_answers(user1_id, user2_id)

#     user1_scores = await calculate_trait_scores(users_answers[0])
#     user2_scores = await calculate_trait_scores(users_answers[1])

#     return user1_scores, user2_scores


# async def get_trait_scores_self(
#     user_id: str,
# ) -> dict[str, float]:
#     """Get the trait scores for a user.

#     Args:
#         user_id (str): The ID of the user.

#     Returns:
#         dict[str, float]: The trait scores for the user.
#     """
#     users_answers = await get_user_answers(user_id)
#     return await calculate_trait_scores(users_answers)


@router.get("/api/personality/{user_id}")
async def get_personality_profile_route(user_id: str):
    pass


@router.post("/api/personality/question/{question_id}")
async def answer_personality_question_route(question_id: str):
    pass


@router.delete("/api/personality/question/{question_id}")
async def delete_personality_question_answer_route(question_id: str):
    pass


"--------------- CHAT -----------------"


class ConversationType(IntEnum):
    GENERAL_ONE_ON_ONE = 0
    GENERAL_GROUP = 1
    DATING_ONE_ON_ONE = 2


class ChatActionType(IntEnum):
    MESSAGE = 0
    TYPING = 1
    REACTION = 2
    USER_JOINED = 3
    USER_LEFT = 4
    OPEN_CONVERSATION = 5


class ChatActionMessageRequest(BaseModel):
    content: str
    reply_to_id: str | None = None
    attached_post_id: str | None = None
    attached_media_url: list[str] | None = None
    created_at: datetime


class ChatActionMessageResponse(ChatActionMessageRequest):
    message_id: str


class ChatActionReaction(BaseModel):
    message_id: str
    reaction_emoji: str


class ChatActionTyping(BaseModel):
    is_typing: bool


class BaseChatAction(BaseModel):
    conversation_id: str
    user_id: str
    action_type: ChatActionType


class ChatActionRequest(BaseChatAction):
    action_data: ChatActionMessageRequest | ChatActionReaction | ChatActionTyping | str


class ChatActionResponse(BaseChatAction):
    action_data: ChatActionMessageResponse | ChatActionReaction | ChatActionTyping | SimpleUserResponse | str


class Conversation(BaseModel):
    conversation_id: str
    title: str | None = None  # Only for GENERAL_GROUP
    image_url: str | None = None  # Only for GENERAL_GROUP
    conversation_type: ConversationType
    participants: list[SimpleUserResponse]
    admins: list[SimpleUserResponse]
    created_at: datetime
    updated_at: datetime


class CreateConversationInitialMessageRequest(BaseModel):
    content: str
    attached_post_id: str | None = None
    attached_media_url: list[str] | None = None
    created_at: datetime


class CreateConversationRequest(BaseModel):
    conversation_type: ConversationType
    participants: list[str]
    initial_message: CreateConversationInitialMessageRequest
    title: str | None = None
    image_url: str | None = None


class SimpleConversationResponse(BaseModel):
    conversation_id: str
    title: str | None = None
    image_url: str | None = None
    participants: list[SimpleUserResponse]
    created_at: datetime
    updated_at: datetime


class MessageReaction(BaseModel):
    emoji: str
    count: int


class AttachedPostPreview(BaseModel):
    post_id: UUID
    content_preview: str | None
    author_id: UUID
    author_username: str
    created_at: datetime
    is_visible: bool


class ReplyToMessagePreview(BaseModel):
    message_id: UUID
    content_preview: str
    sender_id: UUID
    sender_username: str
    created_at: datetime


class Message(BaseModel):
    message_id: UUID
    content: str
    sender_id: UUID
    sender_username: str
    created_at: datetime
    reactions: list[MessageReaction]
    attached_post: AttachedPostPreview | None
    reply_to: ReplyToMessagePreview | None


class ChatResponse(BaseModel):
    conversation_id: UUID
    conversation_type: ConversationType
    title: str | None
    image_url: str | None
    participants: list[SimpleUserResponse]
    messages: list[Message]
    has_more: bool
    next_cursor: str | None


class SendMessageRequest(BaseModel):
    content: str
    attached_post_id: UUID | None = None
    reply_to_message_id: UUID | None = None
    attached_media_urls: list[str] | None = None


class MessageResponse(BaseModel):
    message_id: UUID
    content: str
    sender_id: UUID
    sender_username: str
    created_at: datetime
    attached_post_id: UUID | None
    reply_to_message_id: UUID | None
    attached_media_urls: list[str] | None


@router.get("/api/chat/{conversation_id}", response_model=ChatResponse)
async def get_chat_messages(
    conversation_id: UUID,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> ChatResponse:
    async with driver.session() as session:
        # First, check if the user is a participant in the conversation
        participant_check_query = """
        MATCH (u:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
        RETURN c.conversation_type AS conversation_type, c.title AS title, c.image_url AS image_url
        """
        result = await session.run(
            participant_check_query,
            {"user_id": str(verified_user.user_id), "conversation_id": str(conversation_id)},
        )
        conversation_data = await result.single()
        if not conversation_data:
            raise HTTPException(status_code=403, detail="You are not a participant in this conversation")

        # Fetch participants
        participants_query = """
        MATCH (u:User)-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
        RETURN u.user_id AS user_id, u.username AS username, u.display_name AS display_name, u.profile_photo AS profile_photo
        """
        participants_result = await session.run(participants_query, {"conversation_id": str(conversation_id)})
        participants = [SimpleUserResponse(**p) for p in await participants_result.data()]

        # Fetch messages with pagination
        messages_query = """
        MATCH (m:Message)-[:IN]->(c:Conversation {conversation_id: $conversation_id})
        WHERE m.created_at < $cursor
        WITH m
        ORDER BY m.created_at DESC
        LIMIT $limit + 1

        OPTIONAL MATCH (sender:User)-[:SENT]->(m)
        OPTIONAL MATCH (m)-[:ATTACHED_TO_POST]->(p:Post)
        OPTIONAL MATCH (p)<-[:POSTED]-(post_author:User)
        OPTIONAL MATCH (m)-[:REPLY_TO_MESSAGE]->(reply:Message)
        OPTIONAL MATCH (reply)<-[:SENT]-(reply_sender:User)
        OPTIONAL MATCH (m)<-[r:REACTED]-(reactor:User)

        WITH m, sender, p, post_author, reply, reply_sender,
             collect(DISTINCT {emoji: r.emoji, reactor_id: reactor.user_id}) AS reactions

        RETURN m.message_id AS message_id,
               m.content AS content,
               m.created_at AS created_at,
               sender.user_id AS sender_id,
               sender.username AS sender_username,
               p.post_id AS attached_post_id,
               p.content AS attached_post_content,
               post_author.user_id AS attached_post_author_id,
               post_author.username AS attached_post_author_username,
               p.created_at AS attached_post_created_at,
               reply.message_id AS reply_to_id,
               reply.content AS reply_to_content,
               reply_sender.user_id AS reply_to_sender_id,
               reply_sender.username AS reply_to_sender_username,
               reply.created_at AS reply_to_created_at,
               reactions
        ORDER BY m.created_at DESC
        """

        cursor_value = cursor if cursor else datetime.now(UTC).isoformat()
        messages_result = await session.run(
            messages_query,
            {"conversation_id": str(conversation_id), "cursor": cursor_value, "limit": limit},
        )
        messages_data: list[dict[str, Any]] = await messages_result.data()

        # Process messages
        messages: list[Message] = []
        for message in messages_data[:limit]:  # Limit to requested amount
            # Process reactions
            reaction_counts: dict[str, int] = {}
            for reaction in message["reactions"]:
                emoji: str = reaction["emoji"]
                if emoji not in reaction_counts:
                    reaction_counts[emoji] = 0
                reaction_counts[emoji] += 1
            reactions = [MessageReaction(emoji=emoji, count=count) for emoji, count in reaction_counts.items()]

            # Check if attached post is visible
            attached_post = None
            if message["attached_post_id"]:
                is_visible = await is_post_visible(message["attached_post_author_id"], verified_user.user_id)
                content_preview = message["attached_post_content"][:100] if is_visible else None
                attached_post = AttachedPostPreview(
                    post_id=UUID(message["attached_post_id"]),
                    content_preview=content_preview,
                    author_id=UUID(message["attached_post_author_id"]),
                    author_username=message["attached_post_author_username"],
                    created_at=message["attached_post_created_at"],
                    is_visible=is_visible,
                )

            # Process reply to message
            reply_to = None
            if message["reply_to_id"]:
                reply_to = ReplyToMessagePreview(
                    message_id=UUID(message["reply_to_id"]),
                    content_preview=message["reply_to_content"][:100],
                    sender_id=UUID(message["reply_to_sender_id"]),
                    sender_username=message["reply_to_sender_username"],
                    created_at=message["reply_to_created_at"],
                )

            messages.append(
                Message(
                    message_id=UUID(message["message_id"]),
                    content=message["content"],
                    sender_id=UUID(message["sender_id"]),
                    sender_username=message["sender_username"],
                    created_at=message["created_at"],
                    reactions=reactions,
                    attached_post=attached_post,
                    reply_to=reply_to,
                ),
            )

        # Determine if there are more messages
        has_more = len(messages_data) > limit
        next_cursor = messages[-1].created_at.isoformat() if has_more else None

        # Mark conversation as read
        await mark_conversation_as_read(str(conversation_id), str(verified_user.user_id))

        return ChatResponse(
            conversation_id=conversation_id,
            conversation_type=ConversationType(conversation_data["conversation_type"]),
            title=conversation_data["title"],
            image_url=conversation_data["image_url"],
            participants=participants,
            messages=messages,
            has_more=has_more,
            next_cursor=next_cursor,
        )


async def is_post_visible(post_author_id: str, viewer_id: str) -> bool:
    query = """
    MATCH (author:User {user_id: $post_author_id}), (viewer:User {user_id: $viewer_id})
    RETURN
        NOT EXISTS((author)-[:BLOCKS]-(viewer)) AND
        (NOT author.account_private OR EXISTS((viewer)-[:FOLLOWS]->(author))) AS is_visible
    """
    result = await driver.session().run(query, {"post_author_id": post_author_id, "viewer_id": viewer_id})
    record = await result.single()
    if not record:
        return False
    return record["is_visible"]


async def mark_conversation_as_read(conversation_id: str, user_id: str):
    query = """
    MATCH (u:User {user_id: $user_id})-[r:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
    SET r.last_read = datetime()
    """
    await driver.session().run(query, {"conversation_id": conversation_id, "user_id": user_id})


@router.post("/api/chat/conversation", response_model=Conversation)
async def create_conversation_route(
    request: CreateConversationRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> Conversation:
    async with driver.session() as session:
        # Check if the requesting user is blocked by or has blocked any of the participants
        block_check_query = """
        MATCH (requester:User {user_id: $requester_id})
        MATCH (participant:User)
        WHERE participant.user_id IN $participant_ids
        OPTIONAL MATCH (requester)-[b1:BLOCKS]-(participant)
        OPTIONAL MATCH (participant)-[b2:BLOCKS]-(requester)
        WITH requester, participant, COUNT(b1) + COUNT(b2) AS block_count
        WHERE block_count = 0
        RETURN participant.user_id AS participant_id,
               participant.account_private AS is_private,
               EXISTS((requester)-[:FOLLOWS]->(participant)) AS is_following
        """
        result = await session.run(
            block_check_query,
            {
                "requester_id": verified_user.user_id,
                "participant_ids": request.participants,
            },
        )
        participants_data = await result.data()

        # Filter out participants that are blocked or have blocked the requester
        valid_participants = [p["participant_id"] for p in participants_data]

        # Check if all requested participants are valid
        if set(valid_participants) != set(request.participants):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create conversation with blocked users or users who have blocked you.",
            )

        # Check if the user can create a conversation with private accounts
        for participant in participants_data:
            if participant["is_private"] and not participant["is_following"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create conversation with private accounts you're not following.",
                )

        # Handle one-on-one conversations (both general and dating)
        if request.conversation_type in [ConversationType.GENERAL_ONE_ON_ONE, ConversationType.DATING_ONE_ON_ONE]:
            if len(request.participants) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One-on-one conversations must have exactly one other participant.",
                )

            # Check if a one-on-one conversation already exists
            existing_conversation_query = """
            MATCH (u1:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation {conversation_type: $conversation_type})
            <-[:PARTICIPATES_IN]-(u2:User {user_id: $other_user_id})
            WHERE NOT EXISTS((c)<-[:PARTICIPATES_IN]-(:User))
            OR COUNT((c)<-[:PARTICIPATES_IN]-(:User)) = 2
            RETURN c
            """
            result = await session.run(
                existing_conversation_query,
                {
                    "user_id": verified_user.user_id,
                    "other_user_id": request.participants[0],
                    "conversation_type": request.conversation_type.value,
                },
            )
            existing_conversation = await result.single()

            if existing_conversation:
                # If conversation exists, just add the new message
                return await add_message_to_existing_conversation(
                    existing_conversation["c"]["conversation_id"],
                    verified_user.user_id,
                    request.initial_message,
                )

        # For dating conversations, check if there's a MATCH relationship
        if request.conversation_type == ConversationType.DATING_ONE_ON_ONE:
            match_check_query = """
            MATCH (requester:User {user_id: $requester_id})-[m:MATCH]-(participant:User {user_id: $participant_id})
            RETURN COUNT(m) > 0 AS has_match
            """
            match_result = await session.run(
                match_check_query,
                {
                    "requester_id": verified_user.user_id,
                    "participant_id": request.participants[0],
                },
            )
            match_data = await match_result.single()

            if not match_data or not match_data["has_match"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create a dating conversation without a match.",
                )

        conversation_id = str(uuid4())
        message_id = str(uuid4())
        current_time = datetime.now(UTC).isoformat()

        # Create the conversation and initial message
        create_conversation_query = """
        CREATE (c:Conversation {
            conversation_id: $conversation_id,
            conversation_type: $conversation_type,
            created_at: $created_at,
            updated_at: $updated_at
        })
        """

        if request.conversation_type == ConversationType.GENERAL_GROUP:
            create_conversation_query += """
            SET c.title = $title,
                c.image_url = $image_url
            """

        create_conversation_query += """
        WITH c
        MATCH (u:User)
        WHERE u.user_id IN $participant_ids OR u.user_id = $requester_id
        CREATE (u)-[:PARTICIPATES_IN]->(c)
        WITH c, u
        WHERE u.user_id = $requester_id
        CREATE (u)-[:ADMIN_OF]->(c)
        WITH c
        MATCH (sender:User {user_id: $requester_id})
        CREATE (m:Message {
            message_id: $message_id,
            content: $initial_message_content,
            attached_media_url: $attached_media_url,
            created_at: $message_created_at
        })
        CREATE (sender)-[:SENT]->(m)-[:IN]->(c)
        WITH c, m
        OPTIONAL MATCH (attached_post:Post {post_id: $attached_post_id})
        FOREACH (post IN CASE WHEN attached_post IS NOT NULL THEN [attached_post] ELSE [] END |
            CREATE (m)-[:ATTACHED_TO_POST]->(post)
        )
        RETURN c, m
        """
        result = await session.run(
            create_conversation_query,
            {
                "conversation_id": conversation_id,
                "conversation_type": request.conversation_type.value,
                "created_at": current_time,
                "updated_at": current_time,
                "title": request.title,
                "image_url": request.image_url,
                "participant_ids": request.participants,
                "requester_id": verified_user.user_id,
                "message_id": message_id,
                "initial_message_content": request.initial_message.content,
                "attached_media_url": request.initial_message.attached_media_url,
                "message_created_at": request.initial_message.created_at.isoformat(),
                "attached_post_id": request.initial_message.attached_post_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation.",
            )

        message_data = record["m"]

        # Fetch participants and admins
        participants_query = """
        MATCH (u:User)-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
        OPTIONAL MATCH (u)-[:ADMIN_OF]->(c)
        RETURN u.user_id AS user_id,
               u.username AS username,
               u.display_name AS display_name,
               u.profile_photo AS profile_photo,
               u.created_at AS created_at,
               EXISTS((u)-[:ADMIN_OF]->(c)) AS is_admin
        """
        participants_result = await session.run(
            participants_query,
            {"conversation_id": conversation_id},
        )
        participants_data = await participants_result.data()

        participants = [SimpleUserResponse(**p) for p in participants_data]
        admins = [SimpleUserResponse(**p) for p in participants_data if p["is_admin"]]

        conversation = Conversation(
            conversation_id=conversation_id,
            conversation_type=request.conversation_type,
            participants=participants,
            admins=admins,
            created_at=datetime.fromisoformat(current_time),
            updated_at=datetime.fromisoformat(current_time),
            title=request.title,
            image_url=request.image_url,
        )
        # Publish to "chat.created" queue
        await router.broker.publish(
            {
                "conversation": conversation.model_dump(),
                "initial_message": {
                    "message_id": message_id,
                    "content": message_data["content"],
                    "attached_media_url": message_data["attached_media_url"],
                    "attached_post_id": request.initial_message.attached_post_id,
                    "sender_id": verified_user.user_id,
                    "created_at": message_data["created_at"],
                },
            },
            topic="chat.created",
        )

        return conversation


async def add_message_to_existing_conversation(
    conversation_id: str,
    sender_id: str,
    message: CreateConversationInitialMessageRequest,
) -> Conversation:
    message_id = str(uuid4())
    current_time = datetime.now(UTC).isoformat()

    query = """
    MATCH (c:Conversation {conversation_id: $conversation_id})
    MATCH (sender:User {user_id: $sender_id})
    CREATE (m:Message {
        message_id: $message_id,
        content: $content,
        attached_media_url: $attached_media_url,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(m)-[:IN]->(c)
    SET c.updated_at = $updated_at
    WITH c, m
    OPTIONAL MATCH (attached_post:Post {post_id: $attached_post_id})
    FOREACH (post IN CASE WHEN attached_post IS NOT NULL THEN [attached_post] ELSE [] END |
        CREATE (m)-[:ATTACHED_TO_POST]->(post)
    )
    RETURN c, m
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_id": message_id,
                "content": message.content,
                "attached_media_url": message.attached_media_url,
                "created_at": message.created_at.isoformat(),
                "updated_at": current_time,
                "attached_post_id": message.attached_post_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add message to existing conversation.",
            )

        # Fetch and return the full conversation details
        return await get_conversation_details(conversation_id)


async def get_conversation_details(conversation_id: str) -> Conversation:
    query = """
    MATCH (c:Conversation {conversation_id: $conversation_id})
    OPTIONAL MATCH (c)<-[:PARTICIPATES_IN]-(p:User)
    OPTIONAL MATCH (c)<-[:ADMIN_OF]-(a:User)
    WITH c,
         collect(DISTINCT {
             user_id: p.user_id,
             username: p.username,
             display_name: p.display_name,
             profile_photo: p.profile_photo
         }) AS participants,
         collect(DISTINCT {
             user_id: a.user_id,
             username: a.username,
             display_name: a.display_name,
             profile_photo: a.profile_photo
         }) AS admins
    RETURN {
        conversation_id: c.conversation_id,
        conversation_type: c.conversation_type,
        title: c.title,
        image_url: c.image_url,
        participants: participants,
        admins: admins,
        created_at: c.created_at,
        updated_at: c.updated_at
    } AS conversation
    """
    async with driver.session() as session:
        result = await session.run(query, {"conversation_id": conversation_id})
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation_data = record["conversation"]
        return Conversation(**conversation_data)


@router.delete("/api/chat/conversation/{conversation_id}")
async def delete_conversation_route(conversation_id: str):
    pass


@router.delete("/api/chat/conversation/{conversation_id}/message/{message_id}")
async def delete_conversation_message_route(conversation_id: str, message_id: str):
    pass


@router.post("/api/chat/{conversation_id}/message", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    message: SendMessageRequest,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> MessageResponse:
    async with driver.session() as session:
        # Check if the user is a participant in the conversation
        participant_check_query = """
        MATCH (u:User {user_id: $user_id})-[:PARTICIPATES_IN]->(c:Conversation {conversation_id: $conversation_id})
        RETURN c
        """
        result = await session.run(
            participant_check_query,
            {"user_id": str(verified_user.user_id), "conversation_id": str(conversation_id)},
        )
        if not await result.single():
            raise HTTPException(status_code=403, detail="You are not a participant in this conversation")

        # Create the message
        message_id = uuid4()
        created_at = datetime.now(UTC)

        create_message_query = """
        MATCH (sender:User {user_id: $sender_id})
        MATCH (c:Conversation {conversation_id: $conversation_id})
        CREATE (m:Message {
            message_id: $message_id,
            content: $content,
            created_at: $created_at,
            attached_media_urls: $attached_media_urls
        })
        CREATE (sender)-[:SENT]->(m)-[:IN]->(c)

        WITH m, c, sender

        OPTIONAL MATCH (attached_post:Post {post_id: $attached_post_id})
        FOREACH (post IN CASE WHEN attached_post IS NOT NULL THEN [attached_post] ELSE [] END |
            CREATE (m)-[:ATTACHED_TO_POST]->(post)
        )

        WITH m, c, sender

        OPTIONAL MATCH (reply_to:Message {message_id: $reply_to_message_id})
        FOREACH (reply IN CASE WHEN reply_to IS NOT NULL THEN [reply_to] ELSE [] END |
            CREATE (m)-[:REPLY_TO_MESSAGE]->(reply)
        )

        SET c.updated_at = $created_at

        RETURN m.message_id AS message_id,
               m.content AS content,
               sender.user_id AS sender_id,
               sender.username AS sender_username,
               m.created_at AS created_at,
               m.attached_media_urls AS attached_media_urls
        """

        result = await session.run(
            create_message_query,
            {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "sender_id": str(verified_user.user_id),
                "content": message.content,
                "created_at": created_at.isoformat(),
                "attached_post_id": str(message.attached_post_id) if message.attached_post_id else None,
                "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
                "attached_media_urls": message.attached_media_urls,
            },
        )

        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create message")

        # Publish to "chat.message.new" topic
        await router.broker.publish(
            topic="chat.message.new",
            message={
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
                "sender_id": str(verified_user.user_id),
                "content": message.content,
                "created_at": created_at.isoformat(),
                "attached_post_id": str(message.attached_post_id) if message.attached_post_id else None,
                "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
                "attached_media_urls": message.attached_media_urls,
            },
        )

        return MessageResponse(
            message_id=UUID(record["message_id"]),
            content=record["content"],
            sender_id=UUID(record["sender_id"]),
            sender_username=record["sender_username"],
            created_at=record["created_at"],
            attached_post_id=message.attached_post_id,
            reply_to_message_id=message.reply_to_message_id,
            attached_media_urls=record["attached_media_urls"],
        )


"--------------- STATS -----------------"


@router.get("/api/stats/user/{user_id}")
async def get_user_stats_route(user_id: str):
    pass


"--------------- DATING -----------------"


class DatingSwipeEvent(BaseModel):
    swiped_right: bool
    requesting_user_id: str
    target_user_id: str


def calculate_distance(location1: tuple[float, float], location2: tuple[float, float]) -> float:
    """Calculate the distance between two points on Earth in miles."""
    r = 3959  # Earth's radius in miles (instead of 6371 for kilometers)

    lat1, lon1 = map(radians, location1)
    lat2, lon2 = map(radians, location2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = r * c
    return round(distance, 2)  # Round to 2 decimal places


@router.get("/api/dating/profile/{user_id}")
async def get_dating_profile_route(user_id: str, verified_user: VerifiedUser = Depends(get_current_user)):
    """Get the dating profile for a user."""
    query = """
    MATCH (user:User {user_id: $user_id})
    MATCH (requester:User {user_id: $requester_id})
    OPTIONAL MATCH (user)-[:BLOCKS]-(requester)
    WITH user, requester, COUNT(requester) AS block_count
    WHERE block_count = 0
    WITH user, requester

    RETURN user {
        .user_id,
        .display_name.
        .first_name,
        .last_name,
        .profile_photo,
        .account_private,
        .username,
        .recent_location,
        .dating_photos,
        .dating_bio,
        .height,
        .gender,
        .sexual_orientation,
        .relationship_status,
        .religion,
        .highest_education_level,
        .looking_for,
        .has_children,
        .wants_children,
        .has_tattoos,
        .show_gender,
        .show_sexual_orientation,
        .show_relationship_status,
        .show_religion,
        .show_education,
        .show_looking_for,
        .show_schools,
        .show_has_children,
        .show_wants_children
        } AS user_data, requester.recent_location AS requester_recent_location
    """

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": user_id,
                "requester_id": verified_user.user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or access denied",
            )
        user_data = record["user_data"]
        requester_location = record["requester_recent_location"]
        user_location = user_data["recent_location"]
        distance = None
        if requester_location and user_location:
            distance = calculate_distance(requester_location, user_location)

        response = DetailedDatingProfileResponse(
            user_id=user_data["user_id"],
            display_name=user_data["display_name"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            profile_photo=user_data["profile_photo"],
            account_private=user_data["account_private"],
            username=user_data["username"],
            distance=distance,
            dating_photos=user_data["dating_photos"],
            dating_bio=user_data["dating_bio"],
            height=user_data["height"],
            has_tattoos=user_data["has_tattoos"],
        )
        if user_data["show_gender"]:
            response.gender = user_data["gender"]
        if user_data["show_sexual_orientation"]:
            response.sexual_orientation = user_data["sexual_orientation"]
        if user_data["show_relationship_status"]:
            response.relationship_status = user_data["relationship_status"]
        if user_data["show_religion"]:
            response.religion = user_data["religion"]
        if user_data["show_looking_for"]:
            response.looking_for = user_data["looking_for"]
        if user_data["highest_education_level"]:
            response.highest_education_level = user_data["highest_education_level"]
        if user_data["show_has_children"]:
            response.has_children = user_data["has_children"]
        if user_data["show_wants_children"]:
            response.wants_children = user_data["wants_children"]
        return response


@router.get("/api/dating/matches")
async def get_dating_matches_route(verified_user: VerifiedUser = Depends(get_current_user)):


@router.get("/api/dating/feed", response_model=list[DetailedDatingProfileResponse])
async def get_dating_feed_route(
    cursor: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    verified_user: VerifiedUser = Depends(get_current_user),
) -> list[DetailedDatingProfileResponse]:
    query = """
    // Match the requesting user
    MATCH (user:User {user_id: $user_id})
    MATCH user.dating_active = true

    // Match potential dating profiles
    MATCH (potential:User)
    WHERE potential.dating_active = true
    AND potential.user_id <> user.user_id

    // Privacy checks
    WHERE NOT (user)-[:BLOCKS]-(potential)
    AND NOT (user)-[:SWIPED_LEFT]->(potential)
    AND NOT (user)-[:SWIPED_RIGHT]->(potential)
    AND NOT (user)-[:MATCH]->(potential)

    // Location-based filtering
    WITH user, potential
        point.distance(point({latitude: user.recent_location[0], longitude: user.recent_location[1]}),
            point({latitude: potential.recent_location[0], longitude: potential.recent_location[1]})) / 1609.34AS distance_miles
    WHERE distance_miles <= user.max_distance

    // Preference-based filtering
    WHERE (NOT potential.show_gender OR potential.gender IN user.gender_preferences OR size(user.gender_preferences) = 0)
        AND (NOT potential.show_has_children OR potential.has_children IN user.has_children_preferences OR size(user.has_children_preferences) = 0)
        AND (NOT potential.show_wants_children OR potential.wants_children IN user.wants_children_preferences OR size(user.wants_children_preferences) = 0)
        AND (NOT potential.show_education OR potential.highest_education_level IN user.education_level_preferences OR size(user.education_level_preferences) = 0)
        AND (NOT potential.show_religion OR potential.religion IN user.religion_preferences OR size(user.religion_preferences) = 0)
        AND (NOT potential.show_sexual_orientation OR potential.sexual_orientation IN user.sexual_orientation_preferences OR size(user.sexual_orientation_preferences) = 0)
        AND (NOT potential.show_relationship_status OR potential.relationship_status IN user.relationship_status_preferences OR size(user.relationship_status_preferences) = 0)
        AND (NOT potential.show_looking_for OR potential.looking_for IN user.looking_for_preferences OR size(user.looking_for_preferences) = 0)
        AND (toInteger(potential.height) >= user.minimum_height OR user.minimum_height = 0)
        AND (toInteger(potential.height) <= user.maximum_height OR user.maximum_height = 0)

    // Calculate age
    WITH user, potential, distance_miles,
         duration.between(date(potential.birth_datetime_utc), date()).years AS age
    WHERE age >= user.minimum_age AND age <= user.maximum_age

    // Prioritization factors
    OPTIONAL MATCH (user)-[:FOLLOWS]->(potential)
    OPTIONAL MATCH (potential)-[:FOLLOWS]->(user)
    OPTIONAL MATCH (user)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(potential)
    OPTIONAL MATCH (potential)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(user)
    WITH user, potential, distance_miles, age,
         CASE WHEN (user)-[:FOLLOWS]->(potential) THEN 10 ELSE 0 END +
         CASE WHEN (potential)-[:FOLLOWS]->(user) THEN 8 ELSE 0 END +
         CASE WHEN (user)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(potential) THEN 5 ELSE 0 END +
         CASE WHEN (potential)-[:FOLLOWS]->(:User)-[:FOLLOWS]->(user) THEN 4 ELSE 0 END +
         5 * EXP(-distance_miles / 50) + // Prioritize closer profiles
         10 * EXP(-(duration.inSeconds(datetime() - potential.last_seen).hours / 24)) AS score  // Recency score

    WHERE potential.last_seen < $cursor

    RETURN potential {
        .user_id,
        .display_name,
        .first_name,
        .last_name,
        .profile_photo,
        .account_private,
        .username,
        recent_location: potential.recent_location,
        .dating_photos,
        .dating_bio,
        .height,
        gender: CASE WHEN potential.show_gender THEN potential.gender ELSE null END,
        sexual_orientation: CASE WHEN potential.show_sexual_orientation THEN potential.sexual_orientation ELSE null END,
        relationship_status: CASE WHEN potential.show_relationship_status THEN potential.relationship_status ELSE null END,
        religion: CASE WHEN potential.show_religion THEN potential.religion ELSE null END,
        highest_education_level: CASE WHEN potential.show_education THEN potential.highest_education_level ELSE null END,
        looking_for: CASE WHEN potential.show_looking_for THEN potential.looking_for ELSE null END,
        has_children: CASE WHEN potential.show_has_children THEN potential.has_children ELSE null END,
        wants_children: CASE WHEN potential.show_wants_children THEN potential.wants_children ELSE null END,
        .has_tattoos,
    } AS potential_data, distance_miles, score

    ORDER BY score DESC, potential.last_seen DESC
    LIMIT $limit
    """  # noqa: E501

    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": verified_user.user_id,
                "cursor": cursor.isoformat() if cursor else datetime.now(UTC).isoformat(),
                "limit": limit,
            },
        )

        records = await result.data()

        dating_profiles: list[DetailedDatingProfileResponse] = []
        for record in records:
            profile_data = record["potential_data"]
            profile_data["distance"] = record["distance_miles"]
            dating_profiles.append(DetailedDatingProfileResponse(**profile_data))

        return dating_profiles


class DatingMatchDeleteRequest(BaseModel):
    match_id: str
    requesting_user_id: str


@router.delete("/api/dating/matches/{match_id}")
async def delete_dating_match_route(match_id: str, verified_user: VerifiedUser = Depends(get_current_user)):
    """Delete a dating match."""
    await router.broker.publish(
        topic="dating.delete_match",
        message={
            "match_id": match_id,
            "requesting_user_id": verified_user.user_id,
        },
    )


@router.subscriber("dating.delete_match")
async def delete_match_event(event: DatingMatchDeleteRequest) -> None:
    """TOPIC: dating.delete_match - Subscriber for dating match delete events."""
    match_id = event.match_id
    requesting_user_id = event.requesting_user_id
    query = """
    MATCH (u1:User {user_id: $requesting_user_id})-[m:MATCH {match_id: $match_id}]->(u2:User)
    RETURN m.match_id AS match_id, u2.user_id AS other_user_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "requesting_user_id": requesting_user_id,
                "match_id": match_id,
            },
        )
        record = await result.single()
        if not record:
            logger.error(f"Match not found or user {requesting_user_id} not authorized to delete match {match_id}")
            return

        other_user_id = record["other_user_id"]

        delete_match_query = """
        MATCH (u1:User {user_id: $requesting_user_id})-[m:MATCH {match_id: $match_id}]-(u2:User {user_id: $other_user_id})
        DELETE m
        """

        await session.run(
            delete_match_query,
            {"requesting_user_id": requesting_user_id, "match_id": match_id, "other_user_id": other_user_id},
        )

        delete_conversation_query = """
        MATCH (u1:User {user_id: $requesting_user_id})-[:PARTICIPATES_IN]->(conv:Conversation {conversation_type: $conversation_type})<-[:PARTICIPATES_IN]-(u2:User {user_id: $other_user_id})
        OPTIONAL MATCH (m:Message)-[:IN]->(conv)
        DETACH DELETE m, conv
        """
        await session.run(
            delete_conversation_query,
            {
                "reqeuesting_user_id": requesting_user_id,
                "other_user_id": other_user_id,
                "conversation_type": ConversationType.DATING_ONE_ON_ONE.value,
            },
        )


@router.post("/api/dating/swipe", response_model=WasSuccessfulResponse)
async def swipe_dating_profile_route(
    request: DatingSwipeEvent,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> WasSuccessfulResponse:
    """TOPIC: dating.swipe - Endpoint for dating swipe events."""
    request.requesting_user_id = verified_user.user_id
    await router.broker.publish(
        topic="dating.swipe",
        message=request.model_dump_json(),
    )
    return WasSuccessfulResponse(successful=True)


@router.subscriber("dating.swipe")
async def dating_swipe_event(event: DatingSwipeEvent) -> None:
    """TOPIC: dating.swipe - Subscriber for dating swipe events."""
    user1_id = event.requesting_user_id
    user2_id = event.target_user_id
    swiped_right = event.swiped_right
    swipe_type = "SWIPED_RIGHT" if swiped_right else "SWIPED_LEFT"

    query = f"""
    MATCH (swiper:User {{user_id: $swiper_id}})
    MATCH (target:User {{user_id: $target_id}})
    WHERE NOT (swiper)-[:BLOCKS]-(target)
    WITH swiper, target
    OPTIONAL MATCH (target)-[existing_swipe:SWIPED_RIGHT]->(swiper)
    CREATE (swiper)-[new_swipe:{swipe_type} {{created_at: $created_at}}]->(target)
    WITH swiper, target, existing_swipe, new_swipe
    WHERE $swiped_right AND existing_swipe IS NOT NULL
    MERGE (swiper)-[match:MATCH {{created_at: $created_at}}]->(target)
    RETURN
        CASE WHEN new_swipe IS NOT NULL THEN true ELSE false END AS swipe_recorded,
        CASE WHEN match IS NOT NULL THEN true ELSE false END AS match_recorded
    """
    async with driver.session() as session:
        try:
            result = await session.run(
                query,
                {
                    "swiper_id": user1_id,
                    "target_id": user2_id,
                    "created_at": datetime.now(UTC).isoformat(),
                    "swiped_right": swiped_right,
                },
            )
            record = await result.single()
            if not record:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to swipe user.")

            if not record["swipe_recorded"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot swipe this user.")

            if record["match_created"]:
                await router.broker.publish(
                    topic="dating.new_match",
                    message={
                        "user1_id": event.requesting_user_id,
                        "user2_id": event.target_user_id,
                    },
                )
        except Exception as e:
            logger.error(f"Error in dating swipe: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to swipe user.") from e


"--------------- WEBSOCKETS -----------------"


class ChatManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, dict[str, WebSocket]]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str) -> str:
        await websocket.accept()
        socket_id = str(uuid4())
        async with self.lock:
            if conversation_id not in self.active_connections:
                self.active_connections[conversation_id] = {}
            if user_id not in self.active_connections[conversation_id]:
                self.active_connections[conversation_id][user_id] = {}
            self.active_connections[conversation_id][user_id][socket_id] = websocket
        return socket_id

    async def disconnect(self, conversation_id: str, user_id: str, socket_id: str):
        async with self.lock:
            try:
                if conversation_id in self.active_connections:
                    if user_id in self.active_connections[conversation_id]:
                        if socket_id in self.active_connections[conversation_id][user_id]:
                            websocket = self.active_connections[conversation_id][user_id][socket_id]
                            if websocket:
                                try:
                                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Client disconnected")
                                except WebSocketException as e:
                                    logger.error(f"Error in closing websocket: {e}")
                                del self.active_connections[conversation_id][user_id][socket_id]
                        if not self.active_connections[conversation_id][user_id]:
                            del self.active_connections[conversation_id][user_id]
                    if not self.active_connections[conversation_id]:
                        del self.active_connections[conversation_id]
            except Exception as e:
                logger.error(f"Error in disconnecting websocket: {e}")

    async def broadcast(self, action: ChatActionResponse, conversation_id: str, exclude_socket_id: str):
        if conversation_id in self.active_connections:
            for _, socket_ids in self.active_connections[conversation_id].items():
                for socket_id, websocket in socket_ids.items():
                    if socket_id != exclude_socket_id:
                        await websocket.send_json(action.model_dump_json(), mode="json")

    async def send_to_user(self, action: ChatActionResponse, conversation_id: str, user_id: str):
        if conversation_id in self.active_connections and user_id in self.active_connections[conversation_id]:
            for _, websocket in self.active_connections[conversation_id][user_id].items():
                await websocket.send_json(action.model_dump_json(), mode="json")


class GeneralManager:
    def __init__(self):
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        socket_id = str(uuid4())
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}
            self.active_connections[user_id][socket_id] = websocket
        return socket_id

    async def disconnect(self, user_id: str, socket_id: str):
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

    async def broadcast(self, notification: str, user_id: str):
        """Broadcasts a JSON string to all connected websockets for a given user."""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id].values():
                await websocket.send_json(notification, mode="json")


@router.websocket("/ws/general")
async def websocket_general_endpoint(
    websocket: WebSocket,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """WebSocket endpoint for general chat."""
    logger.info("Received websocket connection for general chat")
    general_manager = GeneralManager()
    socket_id = await general_manager.connect(websocket, verified_user.user_id)
    try:
        while True:
            data = GeneralKafkaWebsocketMessage(**await websocket.receive_json())
            await router.broker.publish(
                topic=data.topic,
                message=data.model_dump_json(),
            )
    except WebSocketException as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await general_manager.disconnect(verified_user.user_id, socket_id)


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    verified_user: VerifiedUser = Depends(get_current_user),
) -> None:
    """WebSocket endpoint for chat."""
    logger.info(f"Received websocket connection for conversation {conversation_id}")
    chat_manager = ChatManager()
    socket_id = await chat_manager.connect(websocket, conversation_id, verified_user.user_id)
    try:
        while True:
            data = ChatActionRequest(**await websocket.receive_json())

            if data.action_type == ChatActionType.TYPING:
                await router.broker.publish(
                    topic="chat.typing",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.MESSAGE:
                await router.broker.publish(
                    topic="chat.message",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.USER_JOINED:
                await router.broker.publish(
                    topic="chat.user_joined",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.USER_LEFT:
                await router.broker.publish(
                    topic="chat.user_left",
                    message=data.model_dump_json(),
                )
            elif data.action_type == ChatActionType.OPEN_CONVERSATION:
                await router.broker.publish(
                    topic="chat.open_conversation",
                    message=data.model_dump_json(),
                )
    except WebSocketException as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await chat_manager.disconnect(conversation_id, verified_user.user_id, socket_id)


"--------------- STORIES -----------------"

"--------------- BOOPS -----------------"


class BoopResponse(BaseModel):
    boop_id: str
    booped_user_id: str
    total_boops: int
    created_at: datetime
    updated_at: datetime
    is_your_turn: bool
    is_new_unread_boop: bool


class BoopedEvent(BaseModel):
    boop_id: str
    booped_user_id: str
    total_boops: int
    created_at: datetime
    updated_at: datetime
    is_your_turn: bool
    is_new_unread_boop: bool


@router.post("/api/boop/{target_user_id}", response_model=BoopResponse)
async def send_boop_route(target_user_id: str, verified_user: VerifiedUser = Depends(get_current_user)) -> BoopResponse:
    async with driver.session() as session:
        # Check if the users can interact (not blocked, follows if private)
        can_interact_query = """
        MATCH (sender:User {user_id: $sender_id}), (receiver:User {user_id: $receiver_id})
        WHERE NOT (sender)-[:BLOCKS]-(receiver)
        AND (NOT receiver.account_private OR (sender)-[:FOLLOWS]->(receiver))
        RETURN COUNT(*) > 0 AS can_interact
        """
        result = await session.run(
            can_interact_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
            },
        )
        record = await result.single()
        if not record or not record["can_interact"]:
            raise HTTPException(status_code=403, detail="You cannot boop someone who you cannot interact with")

        # Check if it's the sender's turn to boop
        turn_check_query = """
        MATCH (sender:User {user_id: $sender_id})-[boop:BOOP_RELATIONSHIP]-(receiver:User {user_id: $receiver_id})
        RETURN boop.last_booper_id <> $sender_id AS is_sender_turn
        """
        result = await session.run(
            turn_check_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to check turn")
        if not record["is_sender_turn"]:
            raise HTTPException(status_code=403, detail="It's not your turn to boop")

        # Create or update the BOOP_RELATIONSHIP
        boop_query = """
        MATCH (sender:User {user_id: $sender_id})
        MATCH (receiver:User {user_id: $receiver_id})
        MERGE (sender)-[boop:BOOP_RELATIONSHIP]-(receiver)
        ON CREATE SET
            boop.boop_id = $boop_id,
            boop.total_boops = 1,
            boop.created_at = $boop_created_at,
            boop.updated_at = $boop_updated_at,
            boop.last_booper_id = $sender_id,
            receiver.unread_boops = COALESCE(receiver.unread_boops, 0) + 1
        ON MATCH SET
            boop.total_boops = boop.total_boops + 1,
            boop.updated_at = $boop_updated_at,
            boop.last_booper_id = $sender_id,
            receiver.unread_boops = CASE
                WHEN boop.last_booper_id <> $sender_id
                THEN COALESCE(receiver.unread_boops, 0) + 1
                ELSE receiver.unread_boops
            END
        RETURN boop.boop_id AS boop_id,
               sender.user_id AS booper_id,
               sender.username AS booper_username,
               boop.total_boops AS total_boops,
               boop.created_at AS boop_created_at,
               boop.updated_at AS boop_updated_at,
               boop.last_booper_id AS last_booper_id,
               receiver.unread_boops AS receiver_unread_boops
        """
        result = await session.run(
            boop_query,
            {
                "sender_id": str(verified_user.user_id),
                "receiver_id": target_user_id,
                "boop_id": str(uuid4()),
                "boop_created_at": datetime.now(UTC),
                "boop_updated_at": datetime.now(UTC),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create boop")
        is_your_turn = record["last_booper_id"] != str(verified_user.user_id)
        is_new_unread_boop = record["receiver_unread_boops"] > 0
        return BoopResponse(
            boop_id=record["boop_id"],
            booped_user_id=target_user_id,
            total_boops=record["total_boops"],
            created_at=record["boop_created_at"],
            updated_at=record["boop_updated_at"],
            is_your_turn=is_your_turn,
            is_new_unread_boop=is_new_unread_boop,
        )


"--------------- EVENTS -----------------"

"""
We're going to have an API route for creating a conversation,
but once it's been created, everything else will be handled via
websockets.

"""


@router.subscriber("chat.message.new")
async def chat_message(event: ChatActionRequest):
    if event.action_type != ChatActionType.MESSAGE:
        raise HTTPException(status_code=400, detail="Invalid action type")

    if not isinstance(event.action_data, ChatActionMessageRequest):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    if not event.action_data.created_at:
        raise HTTPException(status_code=400, detail="Invalid message creation time")

    query = """
    MATCH (conversation:Conversation {conversation_id: $conversation_id})
    MATCH (sender:User {user_id: $sender_id})
    CREATE (message:Message {
        message_id: $message_id,
        content: $content,
        attached_media_url: $attached_media_url,
        created_at: $created_at
    })
    CREATE (sender)-[:SENT]->(message)-[:IN]->(conversation)
    FOREACH (reply_id IN CASE WHEN $reply_to_id IS NOT NULL THEN [$reply_to_id] ELSE [] END |
        MATCH (reply_to:Message {message_id: reply_id})
        CREATE (message)-[:REPLY_TO_MESSAGE]->(reply_to)
    )
    FOREACH (attached_post_id IN CASE WHEN $attached_post_id IS NOT NULL THEN [$attached_post_id] ELSE [] END |
        MATCH (post:Post {post_id: attached_post_id})
        CREATE (message)-[:ATTACHED_TO_POST]->(post)
    )
    RETURN message
    """

    async with driver.session() as session:
        message_id = str(uuid4())
        result = await session.run(
            query,
            {
                "message_id": message_id,
                "conversation_id": event.conversation_id,
                "sender_id": event.user_id,
                "content": event.action_data.content,
                "attached_media_url": event.action_data.attached_media_url,
                "created_at": event.action_data.created_at,
                "reply_to_id": event.action_data.reply_to_id,
                "attached_post_id": event.action_data.attached_post_id,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Message not found")
        response = ChatActionResponse(**record["message"])
        chat_manager = ChatManager()
        await chat_manager.broadcast(response, event.conversation_id, event.user_id)


@router.subscriber("chat.typing")
async def chat_typing(event: ChatActionRequest):
    if event.action_type != ChatActionType.TYPING:
        raise HTTPException(status_code=400, detail="Invalid action type")

    if not isinstance(event.action_data, ChatActionTyping):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    outbound = ChatActionResponse(
        conversation_id=event.conversation_id,
        user_id=event.user_id,
        action_type=ChatActionType.TYPING,
        action_data=event.action_data,
    )
    chat_manager = ChatManager()
    await chat_manager.broadcast(outbound, event.conversation_id, event.user_id)


@router.subscriber("chat.user_joined")
async def chat_user_joined(event: ChatActionRequest):
    if event.action_type != ChatActionType.USER_JOINED:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})
    RETURN user.user_id AS user_id, user.username AS username, user.display_name AS display_name, user.profile_photo AS profile_photo
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.action_data,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = SimpleUserResponse(**record)
        chat_manager = ChatManager()
        # When they're added, the user_id is the one who added them
        # The action_data is the user added
        await chat_manager.broadcast(
            ChatActionResponse(
                conversation_id=event.conversation_id,
                user_id=event.action_data,
                action_type=ChatActionType.USER_JOINED,
                action_data=response,
            ),
            event.conversation_id,
            event.user_id,
        )


@router.subscriber("chat.user_left")
async def chat_user_left(event: ChatActionRequest):
    if event.action_type != ChatActionType.USER_LEFT:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})
    RETURN user.user_id AS user_id, user.username AS username, user.display_name AS display_name, user.profile_photo AS profile_photo
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.action_data,
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = SimpleUserResponse(**record)
        chat_manager = ChatManager()
        await chat_manager.broadcast(
            ChatActionResponse(
                conversation_id=event.conversation_id,
                user_id=event.user_id,
                action_type=ChatActionType.USER_LEFT,
                action_data=response,
            ),
            event.conversation_id,
            event.user_id,
        )


@router.subscriber("chat.open_conversation")
async def chat_open_conversation(event: ChatActionRequest):
    """Mark the conversation notifications as read and sync across user's devices."""
    if event.action_type != ChatActionType.OPEN_CONVERSATION:
        raise HTTPException(status_code=400, detail="Invalid action type")
    if not isinstance(event.action_data, str):
        raise HTTPException(status_code=400, detail="Invalid action data type")

    query = """
    MATCH (user:User {user_id: $user_id})-[:RECEIVED]->(n:Notification)
    WHERE n.reference_id = $conversation_id AND n.notification_type = 'NEW_MESSAGE' AND n.is_read = false
    SET n.is_read = true, n.updated_at = datetime()
    RETURN n.notification_id AS notification_id, n.updated_at AS updated_at
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            {
                "user_id": event.user_id,
                "conversation_id": event.conversation_id,
            },
        )
        records = await result.data()

        if records:
            # Only update the user's other devices if notifications were marked as read
            notification_manager = GeneralManager()
            updated_notifications = [
                NotificationGroup(
                    notification_id=record["notification_id"],
                    notification_type="NEW_MESSAGE",
                    reference_id=event.conversation_id,
                    is_read=True,
                    updated_at=record["updated_at"],
                    action_users=[],  # We don't need to send this information
                    action_count=0,  # We don't need to send this information
                    content_preview=None,  # We don't need to send this information
                )
                for record in records
            ]
            await notification_manager.broadcast(
                NotificationResponse(notifications=updated_notifications, has_more=False, next_cursor=None).model_dump_json(),
                event.user_id,
            )

    # Acknowledge the open conversation action only to the user who opened it
    chat_manager = ChatManager()
    await chat_manager.send_to_user(
        ChatActionResponse(
            conversation_id=event.conversation_id,
            user_id=event.user_id,
            action_type=ChatActionType.OPEN_CONVERSATION,
            action_data="Conversation opened and notifications marked as read",
        ),
        event.conversation_id,
        event.user_id,
    )


class MajorSectionViewed(BaseModel):
    section: str
    user_id: str


class MajorSectionViewedResponse(MajorSectionViewed):
    updated_at: datetime


@router.post("/api/user/major-section/{section}", response_model=None)
async def user_viewed_major_section_route(section: str, verified_user: VerifiedUser = Depends(get_current_user)):
    await router.broker.publish(
        topic="major-section.viewed",
        message={
            "section": section,
            "user_id": verified_user.user_id,
        },
    )


@router.subscriber("major-section.viewed")
async def user_viewed_boops_page_event(event: MajorSectionViewed) -> None:
    """Update the last time a user viewed a major section."""
    general_manager = GeneralManager()

    query = f"""
    MATCH (user:User {{user_id: $user_id}})
    SET user.last_checked_{event.section} = $last_checked
    RETURN user.last_checked_{event.section} as updated_at
    """
    last_checked = datetime.now(UTC)
    literal_query = cast(LiteralString, query)
    async with driver.session() as session:
        result = await session.run(
            literal_query,
            {
                "user_id": event.user_id,
                "last_checked": last_checked.isoformat(),
            },
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        response = MajorSectionViewedResponse(
            section=event.section,
            user_id=event.user_id,
            updated_at=last_checked,
        )
        await general_manager.broadcast(
            response.model_dump_json(),
            event.user_id,
        )


# @router.subscriber("create-or-update-notification")
# async def create_or_update_notification(event: NotificationEvent):
#     query = """
#     MERGE (n:Notification {notification_type: $notification_type, reference_id: $reference_id})
#     ON CREATE SET
#         n.notification_id = apoc.create.uuid(),
#         n.content_preview = $content_preview,
#         n.post_type = $post_type,
#         n.action_count = 1,
#         n.is_read = false,
#         n.updated_at = datetime()
#     ON MATCH SET
#         n.action_count = n.action_count + 1,
#         n.is_read = false,
#         n.updated_at = datetime()

#     WITH n

#     MATCH (target_user:User {user_id: $target_user_id})
#     MERGE (target_user)-[:RECEIVED]->(n)

#     WITH n

#     MATCH (action_user:User {user_id: $action_user_id})
#     MERGE (action_user)-[:ACTED_ON]->(n)

#     RETURN n as notification
#     """
#     async with driver.session() as session:
#         result = await session.run(
#             query,
#             {
#                 "notification_type": event.notification_type,
#                 "reference_id": event.reference_id,
#                 "content_preview": event.content_preview,
#                 "post_type": event.post_type,
#                 "target_user_id": event.target_user_id,
#                 "action_user_id": event.action_user_id,
#             },
#         )
#         record = await result.single()
#         if not record:
#             raise HTTPException(status_code=404, detail="Notification not found")
#         response = NotificationResponse(**record["notification"])
#         notification_manager = NotificationManager()
#         await notification_manager.broadcast(response, event.target_user_id)
