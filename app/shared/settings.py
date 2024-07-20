from dotenv import load_dotenv

load_dotenv()
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
algorithm = "ES256"
APP_ENV = os.getenv("APP_ENV", "")

logger.error(f"APP_ENV: {APP_ENV}")
DEV_JWT_SECRET = os.getenv("DEV_JWT_SECRET", "")
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
    algorithm: str = "ES256"


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
        private_key=DEV_JWT_SECRET,
        algorithm=algorithm,
    )


settings_model = Settings()
private_key = serialization.load_pem_private_key(
    settings_model.jwt.private_key.encode(),
    password=None,
    backend=default_backend(),
)

public_key = private_key.public_key()
pem_public_key = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
