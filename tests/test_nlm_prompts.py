"""Tests for nlm-proxy prompt templates."""

from knowledge_finder_bot.nlm.prompts import (
    REWRITE_SYSTEM_PROMPT,
    REWRITE_USER_TEMPLATE,
)


def test_rewrite_prompt_has_task_prefix():
    """Rewrite user template starts with ### Task: for nlm-proxy routing."""
    assert REWRITE_USER_TEMPLATE.startswith("### Task:")


def test_rewrite_prompt_template_renders():
    """Rewrite user template accepts a question variable."""
    result = REWRITE_USER_TEMPLATE.format(question="Tell me more")
    assert "Tell me more" in result
    assert result.startswith("### Task:")


def test_rewrite_system_prompt_not_empty():
    """System prompt has content for the LLM."""
    assert len(REWRITE_SYSTEM_PROMPT) > 50
    assert "rewrite" in REWRITE_SYSTEM_PROMPT.lower()
