"""Session store for multi-turn conversation IDs."""

from cachetools import TTLCache


class SessionStore:
    """Maps AAD object IDs to nlm-proxy conversation IDs with TTL expiry."""

    def __init__(self, ttl: int = 86400, maxsize: int = 1000) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, aad_id: str) -> str | None:
        """Get conversation_id for a user, or None if not found/expired."""
        return self._cache.get(aad_id)

    def set(self, aad_id: str, conversation_id: str) -> None:
        """Store conversation_id for a user."""
        self._cache[aad_id] = conversation_id

    def clear(self, aad_id: str) -> None:
        """Remove a user's session."""
        self._cache.pop(aad_id, None)
