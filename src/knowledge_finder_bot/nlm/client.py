"""Client for nlm-proxy OpenAI-compatible API."""

from collections.abc import AsyncGenerator

import structlog
from openai import AsyncOpenAI

from knowledge_finder_bot.config import Settings
from knowledge_finder_bot.nlm.models import NLMChunk, NLMResponse

logger = structlog.get_logger()


def _parse_conversation_id(system_fingerprint: str | None) -> str | None:
    """Extract conversation_id from system_fingerprint (format: conv_{id})."""
    if system_fingerprint and system_fingerprint.startswith("conv_"):
        return system_fingerprint[5:]
    return None


class NLMClient:
    """Async client for querying nlm-proxy."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.nlm_proxy_url,
            api_key=settings.nlm_proxy_api_key,
            timeout=settings.nlm_timeout,
        )
        self._model = settings.nlm_model_name

    async def query(
        self,
        user_message: str,
        allowed_notebooks: list[str],
        conversation_id: str | None = None,
        stream: bool = True,
    ) -> NLMResponse:
        """Query nlm-proxy with ACL-filtered notebooks.

        Args:
            user_message: The user's question.
            allowed_notebooks: Notebook IDs the user has access to.
            conversation_id: Optional ID for multi-turn context.
            stream: Use streaming (default True).

        Returns:
            NLMResponse with answer, reasoning, and conversation context.
        """
        extra_body: dict = {"metadata": {"allowed_notebooks": allowed_notebooks}}
        if conversation_id:
            extra_body["conversation_id"] = conversation_id

        logger.info(
            "nlm_query_start",
            model=self._model,
            notebook_count=len(allowed_notebooks),
            notebooks=allowed_notebooks,
            conversation_id=conversation_id,
            stream=stream,
        )

        try:
            if stream:
                return await self._query_streaming(user_message, extra_body)
            return await self._query_non_streaming(user_message, extra_body)
        except Exception:
            logger.error("nlm_query_error", model=self._model)
            raise

    async def query_stream(
        self,
        user_message: str,
        allowed_notebooks: list[str],
        conversation_id: str | None = None,
    ) -> AsyncGenerator[NLMChunk, None]:
        """Stream nlm-proxy response as individual chunks.

        Yields NLMChunk objects as they arrive from the SSE stream.
        The caller is responsible for accumulating text.
        """
        extra_body: dict = {"metadata": {"allowed_notebooks": allowed_notebooks}}
        if conversation_id:
            extra_body["conversation_id"] = conversation_id

        logger.info(
            "nlm_stream_start",
            model=self._model,
            notebook_count=len(allowed_notebooks),
            notebooks=allowed_notebooks,
            conversation_id=conversation_id,
        )

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": user_message}],
            stream=True,
            extra_body=extra_body,
        )

        model_emitted = False
        chunk_count = 0

        async for chunk in stream:
            chunk_count += 1
            chunk_model = chunk.model if chunk.model else None
            sys_fp = chunk.system_fingerprint
            parsed_conv_id = _parse_conversation_id(sys_fp) if sys_fp else None

            logger.debug(
                "nlm_chunk_received",
                chunk_number=chunk_count,
                has_model=chunk_model is not None,
                has_system_fingerprint=sys_fp is not None,
                num_choices=len(chunk.choices),
            )

            if (chunk_model and not model_emitted) or parsed_conv_id:
                if parsed_conv_id:
                    logger.info(
                        "nlm_conversation_id_received",
                        conversation_id=parsed_conv_id,
                        system_fingerprint=sys_fp,
                    )
                logger.debug(
                    "nlm_chunk_meta_emit",
                    chunk_type="meta",
                    model=chunk_model if not model_emitted else None,
                    conversation_id=parsed_conv_id,
                )
                yield NLMChunk(
                    chunk_type="meta",
                    model=chunk_model if not model_emitted else None,
                    conversation_id=parsed_conv_id,
                )
                if chunk_model:
                    model_emitted = True

            for choice in chunk.choices:
                delta = choice.delta

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

        logger.info(
            "nlm_stream_complete",
            model=self._model,
            total_chunks_received=chunk_count,
        )

    async def _query_streaming(
        self, user_message: str, extra_body: dict
    ) -> NLMResponse:
        """Execute streaming query and buffer the response."""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        finish_reason = None
        system_fingerprint = None
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
            if chunk.system_fingerprint:
                system_fingerprint = chunk.system_fingerprint

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

        conversation_id = _parse_conversation_id(system_fingerprint)

        logger.info(
            "nlm_query_complete",
            model=model,
            answer_length=sum(len(p) for p in content_parts),
            has_reasoning=bool(reasoning_parts),
            conversation_id=conversation_id,
            finish_reason=finish_reason,
        )

        return NLMResponse(
            answer="".join(content_parts),
            reasoning="".join(reasoning_parts) if reasoning_parts else None,
            model=model,
            conversation_id=conversation_id,
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
        conversation_id = _parse_conversation_id(response.system_fingerprint)
        reasoning = getattr(message, "reasoning_content", None)

        logger.info(
            "nlm_query_complete",
            model=response.model,
            answer_length=len(message.content or ""),
            has_reasoning=reasoning is not None,
            conversation_id=conversation_id,
            finish_reason=response.choices[0].finish_reason,
        )

        return NLMResponse(
            answer=message.content or "",
            reasoning=reasoning,
            model=response.model,
            conversation_id=conversation_id,
            finish_reason=response.choices[0].finish_reason,
        )
