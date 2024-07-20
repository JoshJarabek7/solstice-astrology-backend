from datetime import UTC, datetime, timedelta

import httpx

from app.shared.settings import settings_model


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
                response = await client.get(str(settings_model.apple.auth_keys_url))
                key_data = response.json()
                self.keys = key_data["keys"]
                self.expiry = datetime.now(UTC) + timedelta(hours=24)
        return self.keys if self.keys is not None else []

key_cache = ApplePublicKeyCache()