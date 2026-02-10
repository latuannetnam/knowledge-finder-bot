"""Tests for nlm response formatter."""

from unittest.mock import MagicMock

from knowledge_finder_bot.nlm.formatter import format_response, format_source_attribution
from knowledge_finder_bot.nlm.models import NLMResponse


def test_format_answer_only():
    """Format with answer only, no ACL service."""
    response = NLMResponse(
        answer="The leave policy allows 20 days per year.",
        model="knowledge-finder",
    )
    result = format_response(response)
    assert result == "The leave policy allows 20 days per year."


def test_format_with_source_attribution():
    """Format with reasoning that matches a notebook name."""
    response = NLMResponse(
        answer="The leave policy allows 20 days per year.",
        reasoning="hr-notebook",
        model="knowledge-finder",
    )
    acl_service = MagicMock()
    acl_service.get_notebook_name.return_value = "HR Docs"

    result = format_response(response, acl_service)
    assert "The leave policy allows 20 days per year." in result
    assert "---" in result
    assert "*Source: HR Docs*" in result


def test_format_with_no_acl_service():
    """Format with reasoning but no ACL service — no source line."""
    response = NLMResponse(
        answer="Answer text.",
        reasoning="hr-notebook",
        model="knowledge-finder",
    )
    result = format_response(response, acl_service=None)
    assert result == "Answer text."
    assert "Source" not in result


def test_format_with_no_matching_notebook():
    """Format when reasoning doesn't match any notebook name."""
    response = NLMResponse(
        answer="Answer text.",
        reasoning="unknown-notebook",
        model="knowledge-finder",
    )
    acl_service = MagicMock()
    acl_service.get_notebook_name.return_value = None

    result = format_response(response, acl_service)
    assert result == "Answer text."
    assert "Source" not in result


def test_format_with_no_reasoning():
    """Format when reasoning is None — no source line even with ACL service."""
    response = NLMResponse(
        answer="Answer text.",
        reasoning=None,
        model="knowledge-finder",
    )
    acl_service = MagicMock()

    result = format_response(response, acl_service)
    assert result == "Answer text."
    assert "Source" not in result


def test_format_source_attribution_known_notebook():
    """Returns formatted source line for known notebook ID."""
    acl_service = MagicMock()
    acl_service.get_notebook_name.return_value = "HR Docs"

    result = format_source_attribution("hr-notebook", acl_service)
    assert result == "\n---\n*Source: HR Docs*"


def test_format_source_attribution_unknown_notebook():
    """Returns None when notebook ID not recognized."""
    acl_service = MagicMock()
    acl_service.get_notebook_name.return_value = None

    result = format_source_attribution("unknown-id", acl_service)
    assert result is None


def test_format_source_attribution_no_acl():
    """Returns None when acl_service is None."""
    result = format_source_attribution("hr-notebook", acl_service=None)
    assert result is None


def test_format_source_attribution_no_notebook_id():
    """Returns None when notebook_id is None."""
    acl_service = MagicMock()
    result = format_source_attribution(None, acl_service)
    assert result is None
