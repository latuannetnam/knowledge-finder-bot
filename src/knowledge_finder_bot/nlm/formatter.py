"""Format nlm-proxy responses for display."""

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.nlm.models import NLMResponse


def format_response(response: NLMResponse, acl_service: ACLService | None = None) -> str:
    """Format an NLMResponse as plain markdown.

    Args:
        response: The parsed nlm-proxy response.
        acl_service: Optional ACL service for notebook name lookup.

    Returns:
        Formatted markdown string.
    """
    parts = [response.answer]

    # Add source attribution if reasoning contains notebook info
    if response.reasoning and acl_service:
        notebook_name = acl_service.get_notebook_name(response.reasoning)
        if notebook_name:
            parts.append(f"\n---\n*Source: {notebook_name}*")

    return "".join(parts)


def format_source_attribution(
    notebook_id: str | None,
    acl_service: ACLService | None = None,
) -> str | None:
    """Return source attribution line for a notebook, or None."""
    if notebook_id and acl_service:
        notebook_name = acl_service.get_notebook_name(notebook_id)
        if notebook_name:
            return f"\n---\n*Source: {notebook_name}*"
    return None
