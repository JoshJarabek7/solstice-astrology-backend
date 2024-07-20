import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
from jwt.algorithms import RSAAlgorithm
from loguru import logger

from app.shared.apple_key_cache import key_cache
from app.shared.settings import pem_public_key, settings_model
from app.users.schemas import AppleTokenRequest, AppleTokenResponse, RefreshTokenRequest, TokenResponse, VerifiedUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
algorithm = "ES256"
APP_ENV = os.getenv("APP_ENV", "")

def create_dev_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(days=30),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(
        payload,
        settings_model.jwt.private_key,
        algorithm="ES256",
    )


async def get_dev_user(token: str = Security(oauth2_scheme)) -> VerifiedUser:
    try:
        payload = jwt.decode(token, settings_model.jwt.private_key, algorithms=["ES256"])
        logger.debug(f"Decoded payload: {payload}")
        return VerifiedUser(user_id=payload["sub"], apple_id=payload["sub"])
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired token.",
        ) from err
    except jwt.InvalidTokenError:
        logger.debug(f"Invalid token: {token}")
        raise HTTPException(status_code=400, detail="Invalid ID token.")


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

    headers = {"kid": str(settings_model.apple.key_id)}

    payload = {
        "iss": str(settings_model.apple.team_id),
        "iat": now,
        "exp": expiration_time,
        "aud": str(settings_model.apple.issuer),
        "sub": str(settings_model.apple.client_id),
        "user_id": user_id,
    }

    return jwt.encode(
        payload,
        str(settings_model.jwt.private_key),
        algorithm="ES256",
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
            str(settings_model.apple.auth_token_url),
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
                str(settings_model.apple.auth_keys_url),
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
            algorithms=[settings_model.jwt.algorithm],
            audience=str(settings_model.apple.client_id),
            issuer=str(settings_model.apple.issuer),
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
        "client_id": str(settings_model.apple.client_id),
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        response = await client.post(
            str(settings_model.apple.auth_token_url),
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
                    audience=str(settings_model.apple.client_id),
                    issuer=str(settings_model.apple.issuer),
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


async def refresh_user(token_data: RefreshTokenRequest) -> TokenResponse:
    refresh_token = token_data.refresh_token
    try:
        decoded_token = jwt.decode(
            refresh_token,
            pem_public_key,
            algorithms=["ES256"],
            audience=settings_model.apple.client_id,
            issuer=str(settings_model.apple.issuer),
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
            str(settings_model.jwt.private_key),
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
