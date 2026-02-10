"""Data models for nlm-proxy responses."""

from pydantic import BaseModel


class NLMResponse(BaseModel):
    """Parsed response from nlm-proxy."""

    answer: str
    reasoning: str | None = None
    model: str
    conversation_id: str | None = None
    finish_reason: str | None = None
