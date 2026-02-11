"""Format nlm-proxy responses for display."""

from microsoft_agents.activity import Attachment
from microsoft_agents.hosting.core.app.streaming.citation import Citation

from knowledge_finder_bot.acl.service import ACLService
from knowledge_finder_bot.nlm.models import NLMResponse

_MAX_REASONING_LENGTH = 15000


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


def build_reasoning_card(reasoning_text: str) -> Attachment:
    """Build an Adaptive Card with collapsible reasoning section.

    Args:
        reasoning_text: Accumulated reasoning content from the LLM.

    Returns:
        Attachment containing the Adaptive Card.
    """
    if len(reasoning_text) > _MAX_REASONING_LENGTH:
        reasoning_text = reasoning_text[:_MAX_REASONING_LENGTH] + "\n\n...(reasoning truncated)"

    card_json = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.ToggleVisibility",
                        "title": "Show reasoning",
                        "targetElements": ["reasoning-container"],
                    }
                ],
            },
            {
                "type": "Container",
                "id": "reasoning-container",
                "isVisible": False,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": reasoning_text,
                        "wrap": True,
                        "size": "Small",
                        "isSubtle": True,
                    }
                ],
            },
        ],
    }

    return Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card_json,
    )


def build_source_citation(
    notebook_id: str | None,
    acl_service: ACLService | None = None,
) -> Citation | None:
    """Build a Citation object for SDK set_citations() API.

    Args:
        notebook_id: The notebook ID from the nlm-proxy response.
        acl_service: ACL service for notebook name lookup.

    Returns:
        Citation object, or None if notebook not found.
    """
    if notebook_id and acl_service:
        notebook_name = acl_service.get_notebook_name(notebook_id)
        if notebook_name:
            return Citation(
                title=notebook_name,
                content=f"Source: {notebook_name}",
            )
    return None
