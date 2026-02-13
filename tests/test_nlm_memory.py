"""Tests for ConversationMemoryManager."""

import time
from unittest.mock import patch

import pytest

from knowledge_finder_bot.nlm.memory import ConversationMemoryManager


def test_get_creates_new_history():
    """get_history creates a new empty history for unknown session."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    history = mgr.get_history("session-1")
    assert len(history.messages) == 0


def test_get_returns_existing_history():
    """get_history returns the same history for the same session."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    h1 = mgr.get_history("session-1")
    h2 = mgr.get_history("session-1")
    assert h1 is h2


def test_add_exchange_stores_messages():
    """add_exchange adds HumanMessage and AIMessage pair."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    mgr.add_exchange("session-1", "What is X?", "X is Y.")

    messages = mgr.get_messages("session-1")
    assert len(messages) == 2
    assert messages[0].content == "What is X?"
    assert messages[0].type == "human"
    assert messages[1].content == "X is Y."
    assert messages[1].type == "ai"


def test_get_messages_empty():
    """get_messages returns empty list for unknown session."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    assert mgr.get_messages("unknown") == []


def test_get_messages_multi_turn():
    """Multiple exchanges are accumulated in order."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    mgr.add_exchange("s1", "Q1", "A1")
    mgr.add_exchange("s1", "Q2", "A2")

    messages = mgr.get_messages("s1")
    assert len(messages) == 4
    assert messages[0].content == "Q1"
    assert messages[1].content == "A1"
    assert messages[2].content == "Q2"
    assert messages[3].content == "A2"


def test_clear_session():
    """clear removes the session from the cache."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    mgr.add_exchange("s1", "Q", "A")
    mgr.clear("s1")
    assert mgr.get_messages("s1") == []


def test_clear_nonexistent_session():
    """Clearing a nonexistent session is a no-op."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    mgr.clear("nonexistent")  # should not raise


def test_ttl_eviction():
    """Sessions are evicted after TTL expires."""
    mgr = ConversationMemoryManager(ttl=1, maxsize=100)
    mgr.add_exchange("s1", "Q", "A")
    assert len(mgr.get_messages("s1")) == 2

    # Wait for TTL to expire
    time.sleep(1.1)
    assert mgr.get_messages("s1") == []


def test_maxsize_eviction():
    """Oldest sessions are evicted when maxsize is exceeded."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=2)
    mgr.add_exchange("s1", "Q1", "A1")
    mgr.add_exchange("s2", "Q2", "A2")
    mgr.add_exchange("s3", "Q3", "A3")  # should evict s1

    assert mgr.get_messages("s1") == []  # evicted
    assert len(mgr.get_messages("s2")) == 2
    assert len(mgr.get_messages("s3")) == 2


def test_separate_sessions_independent():
    """Different sessions maintain independent histories."""
    mgr = ConversationMemoryManager(ttl=3600, maxsize=100)
    mgr.add_exchange("user-a", "Q-A", "A-A")
    mgr.add_exchange("user-b", "Q-B", "A-B")

    assert len(mgr.get_messages("user-a")) == 2
    assert len(mgr.get_messages("user-b")) == 2
    assert mgr.get_messages("user-a")[0].content == "Q-A"
    assert mgr.get_messages("user-b")[0].content == "Q-B"
