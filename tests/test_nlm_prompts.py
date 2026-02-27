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


def test_followup_prompt_has_task_prefix():
    """Follow-up user template starts with ### Task: for nlm-proxy routing."""
    from knowledge_finder_bot.nlm.prompts import FOLLOWUP_USER_TEMPLATE

    assert FOLLOWUP_USER_TEMPLATE.startswith("### Task:")


def test_followup_prompt_template_renders():
    """Follow-up user template accepts question and answer variables."""
    from knowledge_finder_bot.nlm.prompts import FOLLOWUP_USER_TEMPLATE

    result = FOLLOWUP_USER_TEMPLATE.format(question="What is X?", answer="X is Y.")
    assert "What is X?" in result
    assert "X is Y." in result
    assert result.startswith("### Task:")


def test_followup_system_prompt_not_empty():
    """Follow-up system prompt has content for the LLM."""
    from knowledge_finder_bot.nlm.prompts import FOLLOWUP_SYSTEM_PROMPT

    assert len(FOLLOWUP_SYSTEM_PROMPT) > 50
    assert "follow-up" in FOLLOWUP_SYSTEM_PROMPT.lower()

