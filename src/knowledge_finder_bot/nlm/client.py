"""Client for nlm-proxy OpenAI-compatible API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import structlog
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from knowledge_finder_bot.config import Settings
from knowledge_finder_bot.nlm.models import NLMChunk, NLMResponse

if TYPE_CHECKING:
    from knowledge_finder_bot.nlm.memory import ConversationMemoryManager

logger = structlog.get_logger()


class NLMClient:
    """Async client for querying nlm-proxy.

    Uses AsyncOpenAI (raw SDK) for query/streaming to preserve
    reasoning_content from SSE deltas. Uses ChatOpenAI (LangChain)
    for rewrite/followup which only need content.
    """

    def __init__(
        self,
        settings: Settings,
        memory: ConversationMemoryManager | None = None,
        enable_rewrite: bool = True,
        enable_followup: bool = False,
    ) -> None:
        # Raw client for query/streaming — preserves reasoning_content
        self._client = AsyncOpenAI(
            base_url=settings.nlm_proxy_url,
            api_key=settings.nlm_proxy_api_key,
            timeout=settings.nlm_timeout,
        )
        # LangChain client for rewrite/followup — message-based features
        self._llm = ChatOpenAI(
            base_url=settings.nlm_proxy_url,
            api_key=settings.nlm_proxy_api_key,
            model=settings.nlm_model_name,
            timeout=settings.nlm_timeout,
            streaming=True,
        )
        self._model = settings.nlm_model_name
        self._memory = memory
        self._enable_rewrite = enable_rewrite
        self._enable_followup = enable_followup

    def _build_extra_body(
        self,
        allowed_notebooks: list[str],
        chat_id: str | None = None,
    ) -> dict:
        """Build the extra_body metadata dict for nlm-proxy."""
        return {
            "metadata": {
                "allowed_notebooks": allowed_notebooks,
                "chat_id": chat_id,
            }
        }

    async def query(
        self,
        user_message: str,
        allowed_notebooks: list[str],
        chat_id: str | None = None,
        session_id: str | None = None,
        stream: bool = True,
    ) -> NLMResponse:
        """Query nlm-proxy with ACL-filtered notebooks.

        Args:
            user_message: The user's question.
            allowed_notebooks: Notebook IDs the user has access to.
            chat_id: Stable user identifier for session management in nlm-proxy.
            session_id: Session identifier for conversation memory.
            stream: Use streaming (default True).

        Returns:
            NLMResponse with answer, reasoning, and model info.
        """
        extra_body = self._build_extra_body(allowed_notebooks, chat_id)

        logger.info(
            "nlm_query_start",
            model=self._model,
            notebook_count=len(allowed_notebooks),
            notebooks=allowed_notebooks,
            chat_id=chat_id,
            session_id=session_id,
            stream=stream,
        )

        try:
            # Rewrite question if memory has history
            rewritten_question = None
            actual_message = user_message
            if (
                self._enable_rewrite
                and self._memory
                and session_id
                and self._memory.get_messages(session_id)
            ):
                rewritten = await self._rewrite_question(
                    user_message, session_id, extra_body
                )
                if rewritten and rewritten != user_message:
                    rewritten_question = rewritten
                    actual_message = rewritten
                    logger.info(
                        "nlm_question_rewritten",
                        original=user_message[:100],
                        rewritten=rewritten[:100],
                    )

            if stream:
                result = await self._query_streaming(actual_message, extra_body)
            else:
                result = await self._query_non_streaming(actual_message, extra_body)

            result.rewritten_question = rewritten_question

            # Generate follow-up questions
            if self._enable_followup:
                followups = await self._generate_followups(
                    user_message, result.answer, extra_body
                )
                if followups:
                    result.follow_up_questions = followups

            # Store exchange in memory for future context
            if self._memory and session_id:
                self._memory.add_exchange(session_id, user_message, result.answer)

            return result
        except Exception:
            logger.error("nlm_query_error", model=self._model)
            raise

    async def generate_followups(
        self,
        question: str,
        answer: str,
        allowed_notebooks: list[str],
        chat_id: str | None = None,
    ) -> list[str] | None:
        """Generate follow-up question suggestions.

        Public convenience method for use after streaming queries,
        where follow-ups can't be generated inline.

        Returns a list of follow-up questions, or None if disabled/failed.
        """
        if not self._enable_followup:
            return None
        extra_body = self._build_extra_body(allowed_notebooks, chat_id)
        return await self._generate_followups(question, answer, extra_body)

    def clear_session(self, session_id: str) -> bool:
        """Clear conversation memory for a session.

        Returns True if memory was cleared, False if no memory existed.
        """
        if self._memory:
            had_history = bool(self._memory.get_messages(session_id))
            self._memory.clear(session_id)
            return had_history
        return False

    async def query_stream(
        self,
        user_message: str,
        allowed_notebooks: list[str],
        chat_id: str | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[NLMChunk, None]:
        """Stream nlm-proxy response as individual chunks.

        Yields NLMChunk objects as they arrive from the SSE stream.
        The caller is responsible for accumulating text.
        """
        extra_body = self._build_extra_body(allowed_notebooks, chat_id)

        # Rewrite question if memory has history
        actual_message = user_message
        if (
            self._enable_rewrite
            and self._memory
            and session_id
            and self._memory.get_messages(session_id)
        ):
            rewritten = await self._rewrite_question(
                user_message, session_id, extra_body
            )
            if rewritten and rewritten != user_message:
                actual_message = rewritten
                logger.info(
                    "nlm_question_rewritten",
                    original=user_message[:100],
                    rewritten=rewritten[:100],
                )

        logger.info(
            "nlm_stream_start",
            model=self._model,
            notebook_count=len(allowed_notebooks),
            notebooks=allowed_notebooks,
            chat_id=chat_id,
        )

        model_emitted = False
        chunk_count = 0
        content_parts: list[str] = []

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": actual_message}],
            stream=True,
            extra_body=extra_body,
        )

        async for chunk in stream:
            chunk_count += 1
            chunk_model = chunk.model if chunk.model else None

            logger.debug(
                "nlm_chunk_received",
                chunk_number=chunk_count,
                has_model=chunk_model is not None,
                num_choices=len(chunk.choices),
            )

            if chunk_model and not model_emitted:
                logger.debug(
                    "nlm_chunk_meta_emit",
                    chunk_type="meta",
                    model=chunk_model,
                )
                yield NLMChunk(
                    chunk_type="meta",
                    model=chunk_model,
                )
                model_emitted = True

            for choice in chunk.choices:
                delta = choice.delta

                # reasoning_content is in OpenAI o1/o3 format (from nlm-proxy)
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    logger.debug(
                        "nlm_chunk_reasoning_emit",
                        chunk_type="reasoning",
                        text_length=len(reasoning),
                        text_preview=reasoning[:50] if len(reasoning) > 50 else reasoning,
                    )
                    yield NLMChunk(chunk_type="reasoning", text=reasoning)

                if delta.content:
                    content_parts.append(delta.content)
                    logger.debug(
                        "nlm_chunk_content_emit",
                        chunk_type="content",
                        text_length=len(delta.content),
                        text_preview=delta.content[:50] if len(delta.content) > 50 else delta.content,
                    )
                    yield NLMChunk(chunk_type="content", text=delta.content)

                if choice.finish_reason:
                    logger.debug(
                        "nlm_chunk_finish_emit",
                        chunk_type="meta",
                        finish_reason=choice.finish_reason,
                    )
                    yield NLMChunk(
                        chunk_type="meta",
                        finish_reason=choice.finish_reason,
                    )

        # Store exchange in memory after streaming completes
        if self._memory and session_id:
            answer = "".join(content_parts)
            self._memory.add_exchange(session_id, user_message, answer)

        logger.info(
            "nlm_stream_complete",
            model=self._model,
            total_chunks_received=chunk_count,
        )

    async def _rewrite_question(
        self,
        question: str,
        session_id: str,
        extra_body: dict,
    ) -> str | None:
        """Rewrite a follow-up question as standalone using nlm-proxy's llm_task.

        Sends conversation history + rewrite instruction with ### Task: prefix
        to trigger llm_task classification in nlm-proxy's SmartRouter.
        """
        from knowledge_finder_bot.nlm.prompts import (
            REWRITE_SYSTEM_PROMPT,
            REWRITE_USER_TEMPLATE,
        )

        history = self._memory.get_messages(session_id) if self._memory else []
        if not history:
            return None

        messages: list[BaseMessage] = [
            SystemMessage(content=REWRITE_SYSTEM_PROMPT),
            *history,
            HumanMessage(content=REWRITE_USER_TEMPLATE.format(question=question)),
        ]

        logger.debug(
            "nlm_rewrite_start",
            question=question[:100],
            history_length=len(history),
        )

        try:
            response = await self._llm.ainvoke(messages, extra_body=extra_body)
            rewritten = (response.content or "").strip()
            logger.debug(
                "nlm_rewrite_complete",
                rewritten=rewritten[:100],
            )
            return rewritten if rewritten else None
        except Exception:
            logger.warning("nlm_rewrite_failed", question=question[:100])
            return None

    async def _generate_followups(
        self,
        question: str,
        answer: str,
        extra_body: dict,
    ) -> list[str] | None:
        """Generate follow-up question suggestions via nlm-proxy's llm_task.

        Returns a list of 2-3 follow-up questions, or None on failure.
        """
        from knowledge_finder_bot.nlm.prompts import (
            FOLLOWUP_SYSTEM_PROMPT,
            FOLLOWUP_USER_TEMPLATE,
        )

        messages: list[BaseMessage] = [
            SystemMessage(content=FOLLOWUP_SYSTEM_PROMPT),
            HumanMessage(
                content=FOLLOWUP_USER_TEMPLATE.format(
                    question=question, answer=answer[:500]
                )
            ),
        ]

        logger.debug("nlm_followup_start", question=question[:100])

        try:
            response = await self._llm.ainvoke(messages, extra_body=extra_body)
            raw = (response.content or "").strip()
            if not raw:
                return None

            # Parse one question per line, strip numbering/bullets
            followups = []
            for line in raw.split("\n"):
                line = line.strip()
                # Remove common numbering patterns: "1." "1)" "-" "•"
                if line and line[0].isdigit():
                    line = line.lstrip("0123456789.)").strip()
                line = line.lstrip("-•").strip()
                if line and line.endswith("?"):
                    followups.append(line)

            logger.debug(
                "nlm_followup_complete",
                count=len(followups),
            )
            return followups if followups else None
        except Exception:
            logger.warning("nlm_followup_failed", question=question[:100])
            return None

    async def _query_streaming(
        self, user_message: str, extra_body: dict
    ) -> NLMResponse:
        """Execute streaming query and buffer the response."""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        finish_reason = None
        model = self._model

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": user_message}],
            stream=True,
            extra_body=extra_body,
        )

        async for chunk in stream:
            if chunk.model:
                model = chunk.model

            for choice in chunk.choices:
                if choice.finish_reason:
                    finish_reason = choice.finish_reason

                delta = choice.delta
                if delta.content:
                    content_parts.append(delta.content)

                # reasoning_content is in OpenAI o1/o3 format
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    reasoning_parts.append(reasoning)

        logger.info(
            "nlm_query_complete",
            model=model,
            answer_length=sum(len(p) for p in content_parts),
            has_reasoning=bool(reasoning_parts),
            finish_reason=finish_reason,
        )

        return NLMResponse(
            answer="".join(content_parts),
            reasoning="".join(reasoning_parts) if reasoning_parts else None,
            model=model,
            finish_reason=finish_reason,
        )

    async def _query_non_streaming(
        self, user_message: str, extra_body: dict
    ) -> NLMResponse:
        """Execute non-streaming query."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": user_message}],
            stream=False,
            extra_body=extra_body,
        )

        message = response.choices[0].message
        reasoning = getattr(message, "reasoning_content", None)

        logger.info(
            "nlm_query_complete",
            model=response.model,
            answer_length=len(message.content or ""),
            has_reasoning=reasoning is not None,
            finish_reason=response.choices[0].finish_reason,
        )

        return NLMResponse(
            answer=message.content or "",
            reasoning=reasoning,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
        )
