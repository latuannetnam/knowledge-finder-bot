# Clean Streaming Response Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stop leaking LLM reasoning content into the user-visible streamed response; show reasoning in a collapsible Adaptive Card, use SDK-native citations for source attribution, and provide informative status updates during the thinking phase.

**Architecture:** Buffer reasoning chunks server-side instead of streaming them. After the answer stream completes, attach an Adaptive Card with `Action.ToggleVisibility` containing the accumulated reasoning (collapsed by default). Replace text-based source attribution with the SDK's `set_citations()` API on streaming channels. Show "Analyzing your question..." informative update during the reasoning phase so users see activity.

**Tech Stack:** M365 Agents SDK `StreamingResponse` (`set_attachments`, `set_citations`), Adaptive Cards v1.5 (`Action.ToggleVisibility`), `Citation` dataclass from SDK

---

## SDK Reference (verified in .venv)

| API | Import | Notes |
|-----|--------|-------|
| `StreamingResponse.set_attachments(List[Attachment])` | `from microsoft_agents.activity import Attachment` | Sent in final chunk only |
| `StreamingResponse.set_citations(List[Citation])` | `from microsoft_agents.hosting.core.app.streaming.citation import Citation` | Requires `[doc1]` marker in text; SDK converts to `[1]` |
| `Citation` | `from microsoft_agents.hosting.core.app.streaming.citation import Citation` | Fields: `content: str`, `title: Optional[str]`, `url: Optional[str]`, `filepath: Optional[str]` |
| `Attachment` | `from microsoft_agents.activity import Attachment` | Fields: `content_type: str`, `content: Any` |

**Citation pipeline constraint:** The SDK's `CitationUtil.get_used_citations()` filters out citations not referenced in the message text via `[n]` pattern matching. We must append `[doc1]` to the streamed text before calling `end_stream()`.

---

### Task 1: Add `build_reasoning_card()` helper

**Files:**
- Test: `tests/test_formatter.py` (create or append)
- Modify: `src/knowledge_finder_bot/nlm/formatter.py`

**Step 1: Write the failing tests**

Add to `tests/test_formatter.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_formatter.py::test_build_reasoning_card_structure tests/test_formatter.py::test_build_reasoning_card_truncation -v`
Expected: FAIL with `ImportError: cannot import name 'build_reasoning_card'`

**Step 3: Write minimal implementation**

Add to `src/knowledge_finder_bot/nlm/formatter.py`:

```python
from microsoft_agents.activity import Attachment

_MAX_REASONING_LENGTH = 15000


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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_formatter.py::test_build_reasoning_card_structure tests/test_formatter.py::test_build_reasoning_card_truncation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/knowledge_finder_bot/nlm/formatter.py tests/test_formatter.py
git commit -m "feat(formatter): add build_reasoning_card() for collapsible Adaptive Card"
```

---

### Task 2: Add `build_source_citation()` helper

**Files:**
- Test: `tests/test_formatter.py`
- Modify: `src/knowledge_finder_bot/nlm/formatter.py`

**Step 1: Write the failing tests**

Add to `tests/test_formatter.py`:

```python
from unittest.mock import MagicMock

from knowledge_finder_bot.nlm.formatter import build_source_citation


def test_build_source_citation_returns_citation():
    """build_source_citation returns Citation with notebook name."""
    acl = MagicMock()
    acl.get_notebook_name.return_value = "HR Docs"

    citation = build_source_citation("hr-notebook", acl)

    assert citation is not None
    assert citation.title == "HR Docs"
    assert "HR Docs" in citation.content


def test_build_source_citation_returns_none_when_no_notebook():
    """build_source_citation returns None when notebook not found."""
    assert build_source_citation(None, None) is None


def test_build_source_citation_returns_none_when_name_not_found():
    """build_source_citation returns None when ACL has no name for ID."""
    acl = MagicMock()
    acl.get_notebook_name.return_value = None

    assert build_source_citation("unknown-id", acl) is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_formatter.py::test_build_source_citation_returns_citation tests/test_formatter.py::test_build_source_citation_returns_none_when_no_notebook tests/test_formatter.py::test_build_source_citation_returns_none_when_name_not_found -v`
Expected: FAIL with `ImportError: cannot import name 'build_source_citation'`

**Step 3: Write minimal implementation**

Add to `src/knowledge_finder_bot/nlm/formatter.py`:

```python
from microsoft_agents.hosting.core.app.streaming.citation import Citation


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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_formatter.py -v`
Expected: ALL PASS (5 tests: 2 from Task 1 + 3 from Task 2)

**Step 5: Commit**

```bash
git add src/knowledge_finder_bot/nlm/formatter.py tests/test_formatter.py
git commit -m "feat(formatter): add build_source_citation() for SDK citations API"
```

---

### Task 3: Update streaming path — write failing tests first

**Files:**
- Modify: `tests/test_bot_nlm.py`

This task updates the mock fixture and writes the new tests that describe the desired streaming behavior. They will fail until Task 4 changes `bot.py`.

**Step 1: Update `mock_streaming_response` fixture**

In `tests/test_bot_nlm.py`, modify the fixture at line 61-70:

```python
@pytest.fixture
def mock_streaming_response():
    """Mock StreamingResponse capturing all method calls."""
    sr = MagicMock()
    sr.queue_informative_update = MagicMock()
    sr.queue_text_chunk = MagicMock()
    sr.end_stream = AsyncMock()
    sr.set_generated_by_ai_label = MagicMock()
    sr.set_attachments = MagicMock()
    sr.set_citations = MagicMock()
    sr._is_streaming_channel = True
    return sr
```

**Step 2: Rewrite `test_streaming_content_sent_via_queue_text_chunk` (line 115-138)**

Replace with:

```python
@pytest.mark.asyncio
async def test_streaming_only_answer_in_text_chunks(nlm_app, mock_nlm_client, mock_streaming_response):
    """Only content chunks are streamed — reasoning is excluded from text."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    combined = "".join(text_calls)
    # Content should be present
    assert "leave policy" in combined
    assert "allows 20 days" in combined
    # Reasoning must NOT leak into text stream
    assert "Looking in HR docs" not in combined
```

**Step 3: Rewrite `test_streaming_source_attribution_appended` (line 179-198)**

Replace with:

```python
@pytest.mark.asyncio
async def test_streaming_source_via_citations_api(nlm_app, mock_nlm_client, mock_streaming_response):
    """Source attribution uses set_citations() with [doc1] marker in text."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    # set_citations called with one Citation
    mock_streaming_response.set_citations.assert_called_once()
    citations = mock_streaming_response.set_citations.call_args[0][0]
    assert len(citations) == 1
    assert citations[0].title == "HR Docs"

    # Text must contain [doc1] marker for citation rendering
    text_calls = [
        call[0][0] for call in mock_streaming_response.queue_text_chunk.call_args_list
    ]
    combined = "".join(text_calls)
    assert "[doc1]" in combined
```

**Step 4: Rewrite `test_streaming_informative_update_with_notebook_name` (line 141-158)**

Replace with:

```python
@pytest.mark.asyncio
async def test_streaming_informative_updates_notebook_and_reasoning(nlm_app, mock_nlm_client, mock_streaming_response):
    """Two informative updates: notebook search + analyzing question."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    info_calls = [
        call[0][0] for call in mock_streaming_response.queue_informative_update.call_args_list
    ]
    assert len(info_calls) == 2
    assert "HR Docs" in info_calls[0]
    assert "Analyzing" in info_calls[1]
```

**Step 5: Add new test — reasoning in Adaptive Card**

```python
@pytest.mark.asyncio
async def test_streaming_reasoning_in_adaptive_card(nlm_app, mock_nlm_client, mock_streaming_response):
    """Reasoning text sent as collapsible Adaptive Card attachment."""
    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    mock_streaming_response.set_attachments.assert_called_once()
    attachments = mock_streaming_response.set_attachments.call_args[0][0]
    assert len(attachments) == 1
    assert attachments[0].content_type == "application/vnd.microsoft.card.adaptive"

    card_body = attachments[0].content["body"]
    reasoning_container = card_body[1]
    assert reasoning_container["id"] == "reasoning-container"
    assert reasoning_container["isVisible"] is False
    assert "Looking in HR docs" in reasoning_container["items"][0]["text"]
```

**Step 6: Add new test — no reasoning means no card**

```python
@pytest.mark.asyncio
async def test_streaming_no_reasoning_no_card(nlm_app, mock_nlm_client, mock_streaming_response):
    """When no reasoning chunks arrive, no Adaptive Card is attached."""
    async def _content_only_stream(**kwargs):
        yield NLMChunk(chunk_type="meta", model="hr-notebook")
        yield NLMChunk(chunk_type="content", text="Direct answer.")
        yield NLMChunk(chunk_type="meta", conversation_id="conv-456")
        yield NLMChunk(chunk_type="meta", finish_reason="stop")

    mock_nlm_client.query_stream = MagicMock(
        side_effect=lambda **kw: _content_only_stream(**kw)
    )

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_streaming_response,
    ):
        await nlm_app.on_turn(context)

    mock_streaming_response.set_attachments.assert_not_called()
```

**Step 7: Run tests to verify they fail**

Run: `uv run pytest tests/test_bot_nlm.py -v`
Expected: Several FAIL (the old bot.py still streams reasoning into text chunks)

**Step 8: Commit the test changes**

```bash
git add tests/test_bot_nlm.py
git commit -m "test(bot): update streaming tests for clean display behavior"
```

---

### Task 4: Rewrite streaming path in `bot.py`

**Files:**
- Modify: `src/knowledge_finder_bot/bot/bot.py:29,220-254`

**Step 1: Update imports (line 29)**

Change:

```python
from knowledge_finder_bot.nlm.formatter import format_response, format_source_attribution
```

To:

```python
from knowledge_finder_bot.nlm.formatter import (
    format_response,
    format_source_attribution,
    build_reasoning_card,
    build_source_citation,
)
```

**Step 2: Rewrite the streaming path (lines 218-254)**

Replace lines 218-254 (from `notebook_id = None` through `await streaming.end_stream()`) with:

```python
        conversation_id = session_store.get(aad_object_id) if session_store else None
        notebook_id = None
        new_conversation_id = None
        reasoning_text = ""
        reasoning_started = False

        try:
            if use_streaming:
                # Streaming channel (Teams, DirectLine) — use StreamingResponse
                async for chunk in nlm_client.query_stream(
                    user_message=user_message,
                    allowed_notebooks=list(allowed_notebooks),
                    conversation_id=conversation_id,
                ):
                    if chunk.chunk_type == "meta":
                        if chunk.model and notebook_id is None:
                            notebook_id = chunk.model
                            nb_name = acl_service.get_notebook_name(notebook_id)
                            if nb_name:
                                streaming.queue_informative_update(
                                    f"Searching {nb_name}..."
                                )
                        if chunk.conversation_id:
                            new_conversation_id = chunk.conversation_id

                    elif chunk.chunk_type == "reasoning":
                        reasoning_text += chunk.text
                        if not reasoning_started:
                            reasoning_started = True
                            streaming.queue_informative_update(
                                "Analyzing your question..."
                            )

                    elif chunk.chunk_type == "content":
                        streaming.queue_text_chunk(chunk.text)

                # Attach reasoning as collapsible Adaptive Card
                if reasoning_text:
                    streaming.set_attachments(
                        [build_reasoning_card(reasoning_text)]
                    )

                # Source attribution via citations API
                citation = build_source_citation(notebook_id, acl_service)
                if citation:
                    streaming.queue_text_chunk(" [doc1]")
                    streaming.set_citations([citation])

                await streaming.end_stream()
```

**Step 3: Run streaming tests to verify they pass**

Run: `uv run pytest tests/test_bot_nlm.py -k "streaming" -v`
Expected: ALL streaming tests PASS

**Step 4: Commit**

```bash
git add src/knowledge_finder_bot/bot/bot.py
git commit -m "feat(bot): stream only answer content, reasoning to Adaptive Card"
```

---

### Task 5: Update buffered path — write failing tests first

**Files:**
- Modify: `tests/test_bot_nlm.py`

**Step 1: Rewrite `test_buffered_mode_for_non_streaming_channel` (line 270-296)**

Replace with:

```python
@pytest.mark.asyncio
async def test_buffered_mode_answer_without_reasoning(nlm_app, mock_nlm_client):
    """Non-streaming: answer in text, reasoning excluded from text body."""
    mock_sr = MagicMock()
    mock_sr._is_streaming_channel = False
    mock_sr.set_generated_by_ai_label = MagicMock()

    context = create_mock_context(
        activity_type="message",
        text="What is the leave policy?",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_sr,
    ):
        await nlm_app.on_turn(context)

    # Find the Activity object sent (skip typing indicator)
    activity_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if hasattr(call[0][0], "text") and getattr(call[0][0], "type", None) == "message"
    ]
    assert len(activity_calls) == 1
    response = activity_calls[0]

    # Answer text present, reasoning excluded
    assert "leave policy" in response.text
    assert "allows 20 days" in response.text
    assert "Looking in HR docs" not in response.text

    # Reasoning in Adaptive Card attachment
    assert response.attachments is not None
    assert len(response.attachments) == 1
    assert response.attachments[0].content_type == "application/vnd.microsoft.card.adaptive"
```

**Step 2: Rewrite `test_buffered_mode_includes_source_attribution` (line 299-323)**

Replace with:

```python
@pytest.mark.asyncio
async def test_buffered_mode_includes_source_attribution(nlm_app, mock_nlm_client):
    """Non-streaming buffered response includes text-based source attribution."""
    mock_sr = MagicMock()
    mock_sr._is_streaming_channel = False
    mock_sr.set_generated_by_ai_label = MagicMock()

    context = create_mock_context(
        activity_type="message",
        text="Hello",
        aad_object_id="test-aad-id",
    )

    with patch(
        "knowledge_finder_bot.bot.bot.StreamingResponse",
        return_value=mock_sr,
    ):
        await nlm_app.on_turn(context)

    # Find the Activity object sent
    activity_calls = [
        call[0][0] for call in context.send_activity.call_args_list
        if hasattr(call[0][0], "text") and getattr(call[0][0], "type", None) == "message"
    ]
    assert len(activity_calls) == 1
    assert "Source: HR Docs" in activity_calls[0].text
```

**Step 3: Run buffered tests to verify they fail**

Run: `uv run pytest tests/test_bot_nlm.py -k "buffered" -v`
Expected: FAIL (old bot.py still sends raw string, not Activity object)

**Step 4: Commit**

```bash
git add tests/test_bot_nlm.py
git commit -m "test(bot): update buffered mode tests for Activity-based response"
```

---

### Task 6: Rewrite buffered path in `bot.py`

**Files:**
- Modify: `src/knowledge_finder_bot/bot/bot.py:255-284`

**Step 1: Rewrite the buffered path**

Replace lines 255-284 (the `else:` branch through `await context.send_activity(full_text)`) with:

```python
            else:
                # Non-streaming channel (emulator, webchat) — buffer + send_activity
                await context.send_activity(Activity(type="typing"))

                answer_text = ""
                async for chunk in nlm_client.query_stream(
                    user_message=user_message,
                    allowed_notebooks=list(allowed_notebooks),
                    conversation_id=conversation_id,
                ):
                    if chunk.chunk_type == "meta":
                        if chunk.model and notebook_id is None:
                            notebook_id = chunk.model
                        if chunk.conversation_id:
                            new_conversation_id = chunk.conversation_id

                    elif chunk.chunk_type == "reasoning":
                        reasoning_text += chunk.text

                    elif chunk.chunk_type == "content":
                        answer_text += chunk.text

                # Source attribution as text (buffered channels don't support ClientCitation)
                source_line = format_source_attribution(notebook_id, acl_service)
                if source_line:
                    answer_text += source_line

                # Attach reasoning as Adaptive Card if available
                attachments = []
                if reasoning_text:
                    attachments.append(build_reasoning_card(reasoning_text))

                response_activity = Activity(
                    type="message",
                    text=answer_text,
                    attachments=attachments if attachments else None,
                )
                await context.send_activity(response_activity)
```

**Step 2: Also remove the now-unused `sent_separator` variable**

Delete `sent_separator = False` (was line 220). It's no longer needed anywhere.

**Step 3: Run all tests**

Run: `uv run pytest tests/test_bot_nlm.py -v`
Expected: ALL PASS

**Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/knowledge_finder_bot/bot/bot.py
git commit -m "feat(bot): buffered path sends Activity with reasoning card attachment"
```

---

### Task 7: Verify end-to-end and clean up

**Files:**
- Verify: `src/knowledge_finder_bot/nlm/formatter.py` (no unused imports remain)
- Verify: `src/knowledge_finder_bot/bot/bot.py` (clean imports, no dead code)

**Step 1: Run full test suite with coverage**

Run: `uv run pytest tests/ -v --tb=short`
Expected: ALL PASS

**Step 2: Verify no import errors**

Run: `uv run python -c "from knowledge_finder_bot.nlm.formatter import build_reasoning_card, build_source_citation; print('OK')"`
Expected: `OK`

**Step 3: Start bot locally and smoke test**

Run: `uv run python -m knowledge_finder_bot.main`
Expected: Server starts on port 3978, `/health` endpoint responds

**Step 4: Test with Agent Playground (if available)**

Run: `.\run_agentplayground.ps1`
Verify:
- Send a message to the bot
- Answer streams without reasoning content mixed in
- "Show reasoning" Adaptive Card button appears at message end
- Source citation renders (or `[1]` marker visible in non-Teams channels)

**Step 5: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: clean up imports after streaming display refactor"
```

---

## Summary of Changes

| File | What Changes |
|------|-------------|
| `src/knowledge_finder_bot/nlm/formatter.py` | Add `build_reasoning_card()`, `build_source_citation()`, new imports for `Attachment` and `Citation` |
| `src/knowledge_finder_bot/bot/bot.py:29` | Update imports to include new formatter helpers |
| `src/knowledge_finder_bot/bot/bot.py:218-254` | Streaming path: buffer reasoning, stream only content, attach card + citations at end |
| `src/knowledge_finder_bot/bot/bot.py:255-284` | Buffered path: separate reasoning from answer, send `Activity` with card attachment |
| `tests/test_formatter.py` | 5 new tests for `build_reasoning_card()` and `build_source_citation()` |
| `tests/test_bot_nlm.py` | Update fixture (+2 mock methods), rewrite 4 tests, add 2 new tests |

## User Experience Before/After

```
BEFORE:
  Selected notebook: [NetNam] I&I (ID: ed45f03b...)
  Initiating Conversation Response              ← reasoning leaked
  I've registered the user's greeting...        ← reasoning leaked
  ble I&I," and the associated point system...  ← reasoning leaked
  ---
  Chào bạn! Tôi là trợ lý AI...               ← actual answer
  ---
  *Source: HR Docs*                             ← text attribution

AFTER:
  [status: Searching HR Docs...]                ← transient indicator
  [status: Analyzing your question...]          ← transient indicator
  Chào bạn! Tôi là trợ lý AI... [1]           ← clean answer + citation
  [▶ Show reasoning]                            ← collapsed Adaptive Card
    (click to expand reasoning text)
```
