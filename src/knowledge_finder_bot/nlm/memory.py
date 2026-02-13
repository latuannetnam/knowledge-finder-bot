"""Per-session conversation memory with TTL eviction."""

from cachetools import TTLCache
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

import structlog

logger = structlog.get_logger()


class InMemoryChatHistory(BaseChatMessageHistory):
    """Simple in-memory chat message history."""

    def __init__(self) -> None:
        self._messages: list[BaseMessage] = []

    @property
    def messages(self) -> list[BaseMessage]:
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        self._messages.append(message)

    def clear(self) -> None:
        self._messages.clear()


class ConversationMemoryManager:
    """Manages per-session conversation history with TTL eviction.

    Each session (identified by session_id) gets its own ChatMessageHistory.
    Sessions are automatically evicted after `ttl` seconds of inactivity
    or when `maxsize` is exceeded (LRU eviction).
    """

    def __init__(self, ttl: int = 3600, maxsize: int = 1000) -> None:
        self._cache: TTLCache[str, InMemoryChatHistory] = TTLCache(
            maxsize=maxsize, ttl=ttl
        )
        logger.info(
            "memory_manager_initialized",
            ttl=ttl,
            maxsize=maxsize,
        )

    def get_history(self, session_id: str) -> InMemoryChatHistory:
        """Get or create conversation history for a session."""
        if session_id not in self._cache:
            self._cache[session_id] = InMemoryChatHistory()
            logger.debug("memory_session_created", session_id=session_id)
        return self._cache[session_id]

    def add_exchange(
        self, session_id: str, question: str, answer: str
    ) -> None:
        """Store a Q&A exchange in the session history."""
        history = self.get_history(session_id)
        history.add_message(HumanMessage(content=question))
        history.add_message(AIMessage(content=answer))
        logger.debug(
            "memory_exchange_added",
            session_id=session_id,
            message_count=len(history.messages),
        )

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """Get all messages for a session (empty list if no history)."""
        if session_id not in self._cache:
            return []
        return self._cache[session_id].messages

    def clear(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self._cache:
            del self._cache[session_id]
            logger.debug("memory_session_cleared", session_id=session_id)
