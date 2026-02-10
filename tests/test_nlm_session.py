"""Tests for nlm session store."""

import time

import pytest

from knowledge_finder_bot.nlm.session import SessionStore


def test_get_set_basic():
    """Basic get/set operations."""
    store = SessionStore(ttl=300, maxsize=100)
    store.set("user-1", "conv-abc")
    assert store.get("user-1") == "conv-abc"


def test_get_missing_key_returns_none():
    """Missing key returns None."""
    store = SessionStore(ttl=300, maxsize=100)
    assert store.get("nonexistent") is None


def test_clear_session():
    """Clear removes a session."""
    store = SessionStore(ttl=300, maxsize=100)
    store.set("user-1", "conv-abc")
    store.clear("user-1")
    assert store.get("user-1") is None


def test_clear_nonexistent_key_no_error():
    """Clearing a nonexistent key does not raise."""
    store = SessionStore(ttl=300, maxsize=100)
    store.clear("nonexistent")  # Should not raise


def test_ttl_expiry():
    """Expired entries return None."""
    store = SessionStore(ttl=1, maxsize=100)
    store.set("user-1", "conv-abc")
    time.sleep(1.1)
    assert store.get("user-1") is None


def test_overwrite_session():
    """Setting a key twice overwrites the value."""
    store = SessionStore(ttl=300, maxsize=100)
    store.set("user-1", "conv-1")
    store.set("user-1", "conv-2")
    assert store.get("user-1") == "conv-2"
