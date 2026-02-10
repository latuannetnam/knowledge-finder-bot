"""Data models for nlm-proxy responses."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel


@dataclass(slots=True)
class NLMChunk:
    """A single chunk from the nlm-proxy stream."""

    chunk_type: Literal["reasoning", "content", "meta"]
    text: str | None = None
    model: str | None = None
    conversation_id: str | None = None
    finish_reason: str | None = None


class NLMResponse(BaseModel):
    """Parsed response from nlm-proxy."""

    answer: str
    reasoning: str | None = None
    model: str
    conversation_id: str | None = None
    finish_reason: str | None = None
