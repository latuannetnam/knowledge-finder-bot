"""Tests for NLMChunk model."""

from knowledge_finder_bot.nlm.models import NLMChunk


def test_nlm_chunk_content():
    """NLMChunk holds content chunk data."""
    chunk = NLMChunk(chunk_type="content", text="Hello")
    assert chunk.chunk_type == "content"
    assert chunk.text == "Hello"
    assert chunk.model is None


def test_nlm_chunk_meta():
    """NLMChunk holds meta chunk data."""
    chunk = NLMChunk(chunk_type="meta", model="hr-notebook", conversation_id="abc")
    assert chunk.chunk_type == "meta"
    assert chunk.model == "hr-notebook"
    assert chunk.conversation_id == "abc"
    assert chunk.text is None
