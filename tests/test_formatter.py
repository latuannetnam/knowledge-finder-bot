"""Tests for reasoning card and citation builders."""

from knowledge_finder_bot.nlm.formatter import build_reasoning_card


def test_build_reasoning_card_structure():
    """build_reasoning_card returns Adaptive Card with ToggleVisibility."""
    card = build_reasoning_card("Sample reasoning text")

    assert card.content_type == "application/vnd.microsoft.card.adaptive"
    assert card.content["type"] == "AdaptiveCard"
    assert card.content["version"] == "1.5"

    body = card.content["body"]
    # First element: ActionSet with ToggleVisibility button
    assert body[0]["type"] == "ActionSet"
    assert body[0]["actions"][0]["type"] == "Action.ToggleVisibility"
    assert body[0]["actions"][0]["title"] == "Show reasoning"
    assert body[0]["actions"][0]["targetElements"] == ["reasoning-container"]

    # Second element: hidden container with reasoning text
    assert body[1]["type"] == "Container"
    assert body[1]["id"] == "reasoning-container"
    assert body[1]["isVisible"] is False
    assert body[1]["items"][0]["text"] == "Sample reasoning text"
    assert body[1]["items"][0]["wrap"] is True


def test_build_reasoning_card_truncation():
    """Reasoning text exceeding limit is truncated."""
    long_text = "x" * 20000
    card = build_reasoning_card(long_text)

    actual_text = card.content["body"][1]["items"][0]["text"]
    assert len(actual_text) < 20000
    assert actual_text.endswith("...(reasoning truncated)")
