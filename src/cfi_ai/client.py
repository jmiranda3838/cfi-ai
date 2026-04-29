from __future__ import annotations

import logging
import sys
import uuid
from typing import Generator

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from cfi_ai.config import Config

_log = logging.getLogger(__name__)


def is_cache_expired_error(exc: BaseException) -> bool:
    """Check if an exception is caused by an unusable Vertex AI context cache.

    Vertex returns one of two errors when a cached_content reference is no
    longer usable:
      - 400 INVALID_ARGUMENT 'Cache content {N} is expired.' — TTL just
        elapsed, entry still exists server-side.
      - 404 NOT_FOUND 'Not found: cached content metadata for {N}.' — entry
        has been GC'd server-side.
    Both warrant the same recovery: invalidate the local reference and
    rebuild. We walk the cause/context chain to catch wrapped exceptions
    raised through the lazy stream generator.
    """
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, genai_errors.APIError):
            status = getattr(current, "status", None) or ""
            message = getattr(current, "message", None) or ""
            lowered = message.lower()
            if (
                status == "INVALID_ARGUMENT"
                and "cache content" in lowered
                and "is expired" in lowered
            ):
                return True
            if status == "NOT_FOUND" and "cached content" in lowered:
                return True
        msg = str(current).lower()
        if "cache content" in msg and "is expired" in msg:
            return True
        if "cached content metadata" in msg:
            return True
        current = current.__cause__ or current.__context__
    return False


class CacheManager:
    """Manages Gemini explicit context caches for a session."""

    def __init__(self, genai_client: genai.Client, model: str) -> None:
        self._genai_client = genai_client
        self._model = model
        self._caches: dict[str, str] = {}  # key -> cache resource name
        self._all_cache_names: list[str] = []  # track all for cleanup

    def create_cache(self, key: str, system: str, tools: list[types.Tool]) -> None:
        """Create a cached content entry. Raises on failure (caller should catch)."""
        cache = self._genai_client.caches.create(
            model=self._model,
            config=types.CreateCachedContentConfig(
                system_instruction=system,
                tools=tools,
                ttl="3600s",
                display_name=f"cfi-ai-{key}",
            ),
        )
        self._caches[key] = cache.name
        self._all_cache_names.append(cache.name)
        token_count = (
            cache.usage_metadata.total_token_count if cache.usage_metadata else "?"
        )
        _log.info("cache_created key=%s name=%s tokens=%s", key, cache.name, token_count)

    def get_cache_name(self, key: str) -> str | None:
        return self._caches.get(key)

    def invalidate(self, key: str) -> None:
        """Remove a single cache key (e.g. after a cached call fails)."""
        self._caches.pop(key, None)

    def invalidate_all(self) -> None:
        """Forget all local cache references without deleting server-side.

        Use when caches are known to be expired or gone server-side — avoids
        wasteful delete() round-trips that would 404. Also prunes
        _all_cache_names so shutdown's delete_all() does not retry them.
        """
        self._caches.clear()
        self._all_cache_names.clear()

    def reset(self, new_genai_client: genai.Client) -> None:
        """Delete all caches, update the client ref, and clear state."""
        self.delete_all()
        self._genai_client = new_genai_client

    def delete_all(self) -> None:
        """Best-effort delete all caches created during this session."""
        for name in self._all_cache_names:
            try:
                self._genai_client.caches.delete(name=name)
                _log.debug("cache_deleted name=%s", name)
            except Exception as e:
                _log.debug("cache_delete_failed name=%s error=%s", name, e)
        self._all_cache_names.clear()
        self._caches.clear()


def _summarize_contents(messages: list[types.Content]) -> list[str]:
    """Return a PHI-safe per-message summary (index, role, part count, part types).

    Never logs text bodies, file paths, or user content.
    """
    lines: list[str] = []
    for idx, msg in enumerate(messages):
        role = msg.role
        parts = msg.parts or []
        part_summaries: list[str] = []
        for p in parts:
            if p.text is not None:
                part_summaries.append(f"text(len={len(p.text)})")
            elif p.function_call is not None:
                part_summaries.append(f"function_call({p.function_call.name})")
            elif p.function_response is not None:
                part_summaries.append(f"function_response({p.function_response.name})")
            elif p.inline_data is not None:
                mime = p.inline_data.mime_type or "unknown"
                part_summaries.append(f"inline_data({mime})")
            else:
                part_summaries.append("other")
        lines.append(
            f"  msg[{idx}] role={role} parts={len(parts)} [{', '.join(part_summaries)}]"
        )
    return lines


class Client:
    def __init__(self, config: Config) -> None:
        try:
            self._client = genai.Client(
                vertexai=True,
                project=config.project,
                location=config.location,
            )
        except Exception as e:
            print(
                f"Error: Failed to create Vertex AI client: {e}\n"
                "Ensure Application Default Credentials are configured:\n"
                "  gcloud auth application-default login",
                file=sys.stderr,
            )
            sys.exit(1)
        self._model = config.model
        self._max_tokens = config.max_tokens
        self._cache_manager: CacheManager | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def genai_client(self) -> genai.Client:
        return self._client

    @property
    def cache_manager(self) -> CacheManager | None:
        return self._cache_manager

    def set_cache_manager(self, manager: CacheManager) -> None:
        self._cache_manager = manager

    def set_model(self, model: str) -> None:
        """Swap the active model. Caller is responsible for tearing down any
        existing context caches and rebuilding them — caches are bound to the
        previous model, so we drop the local reference here."""
        self._model = model
        self._cache_manager = None

    def stream_response(
        self,
        messages: list[types.Content],
        system: str,
        tools: list[types.Tool],
        *,
        mode: str = "normal",
    ) -> StreamResult:
        """Start a streaming API call. Returns a StreamResult that yields text chunks
        and provides function calls when done."""
        request_id = uuid.uuid4().hex[:8]
        max_tokens = self._max_tokens
        if mode == "map":
            # Map mode needs a generous output budget for multi-file writes;
            # raise the per-call cap above the conversational default.
            max_tokens = max(max_tokens, 65536)
        _log.debug(
            "[req:%s] request mode=%s messages=%d system_len=%d model=%s max_tokens=%d",
            request_id, mode, len(messages), len(system), self._model, max_tokens,
        )
        for line in _summarize_contents(messages):
            _log.debug("[req:%s] %s", request_id, line)

        # Try cached call first if a cache exists
        cache_name = (
            self._cache_manager.get_cache_name("normal")
            if self._cache_manager
            else None
        )

        if cache_name:
            try:
                _log.debug("[req:%s] using cached_content", request_id)
                stream = self._client.models.generate_content_stream(
                    model=self._model,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        cached_content=cache_name,
                        max_output_tokens=max_tokens,
                    ),
                )
                return StreamResult(stream, request_id=request_id)
            except Exception as e:
                if is_cache_expired_error(e):
                    # Let the agent loop refresh caches and retry the request.
                    self._cache_manager.invalidate("normal")
                    _log.info(
                        "[req:%s] cache_expired, propagating for refresh",
                        request_id,
                    )
                    raise
                _log.warning(
                    "[req:%s] cached_call_failed, falling back: %s",
                    request_id, e,
                )
                self._cache_manager.invalidate("normal")

        stream = self._client.models.generate_content_stream(
            model=self._model,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=tools,
                max_output_tokens=max_tokens,
            ),
        )
        return StreamResult(stream, request_id=request_id)

class StreamResult:
    """Wraps the Google Gen AI streaming response to separate text streaming from
    final part extraction."""

    def __init__(self, stream, *, request_id: str = "") -> None:
        self._stream = stream
        self._parts: list[types.Part] = []
        self._finish_reason: str | None = None
        self._usage_metadata: types.GenerateContentResponseUsageMetadata | None = None
        self._grounding_metadata: types.GroundingMetadata | None = None
        self.request_id: str = request_id

    def text_chunks(self) -> Generator[str, None, None]:
        """Yield text delta chunks as they arrive."""
        rid = self.request_id
        buf = ""
        chunk_idx = 0
        for chunk in self._stream:
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                self._usage_metadata = chunk.usage_metadata
            empty_candidates = not chunk.candidates
            if empty_candidates:
                _log.debug("[req:%s] chunk %d empty_candidates=True", rid, chunk_idx)
                continue
            candidate = chunk.candidates[0]
            if candidate.finish_reason:
                self._finish_reason = candidate.finish_reason
            if candidate.grounding_metadata:
                # Gemini streams grounding metadata on the final chunk only; last writer wins.
                self._grounding_metadata = candidate.grounding_metadata
            if not candidate.content or not candidate.content.parts:
                _log.debug(
                    "[req:%s] chunk %d finish_reason=%s no_parts=True",
                    rid, chunk_idx, candidate.finish_reason,
                )
                continue
            for part in candidate.content.parts:
                self._parts.append(part)
                if part.text:
                    chunk_idx += 1
                    buf += part.text
                    part_type = "text"
                elif part.function_call:
                    part_type = f"function_call({part.function_call.name})"
                else:
                    part_type = "other"
                _log.debug(
                    "[req:%s] chunk %d finish_reason=%s part_type=%s text_len=%d cumulative_len=%d",
                    rid, chunk_idx, candidate.finish_reason, part_type,
                    len(part.text) if part.text else 0, len(buf),
                )
                if part.text:
                    yield part.text

    def log_completion(self) -> None:
        """Log a summary of the completed stream."""
        total_text_len = sum(len(p.text) for p in self._parts if p.text)
        fc_count = len(self.function_calls)
        cache_info = ""
        usage = self._usage_metadata
        if usage:
            cached = getattr(usage, "cached_content_token_count", None) or 0
            prompt = getattr(usage, "prompt_token_count", None) or 0
            candidates = getattr(usage, "candidates_token_count", None) or 0
            total = getattr(usage, "total_token_count", None) or 0
            cache_info = (
                f" prompt_tokens={prompt} cached_tokens={cached}"
                f" response_tokens={candidates} total_tokens={total}"
            )
        _log.debug(
            "[req:%s] stream_end total_parts=%d total_text_len=%d function_calls=%d "
            "finish_reason=%s%s",
            self.request_id, len(self._parts), total_text_len, fc_count,
            self._finish_reason, cache_info,
        )

    @property
    def parts(self) -> list[types.Part]:
        """All accumulated parts. Available after text_chunks() is exhausted."""
        return self._parts

    @staticmethod
    def _is_pure_text(p: types.Part) -> bool:
        """A part is eligible for coalescing only if its sole populated field
        is ``text``. Thought parts, thought signatures, function calls,
        inline data, etc. must stay as separate parts because they carry
        semantics that would be lost if merged into a text blob."""
        if not p.text:
            return False
        if getattr(p, "thought", None):
            return False
        if getattr(p, "thought_signature", None):
            return False
        if p.function_call is not None or p.function_response is not None:
            return False
        if p.inline_data is not None:
            return False
        if getattr(p, "executable_code", None) is not None:
            return False
        if getattr(p, "code_execution_result", None) is not None:
            return False
        if getattr(p, "file_data", None) is not None:
            return False
        return True

    @property
    def coalesced_parts(self) -> list[types.Part]:
        """``parts`` with adjacent pure-text parts merged into single parts.

        Gemini can stream a long answer as many small text deltas — preserving
        them one-to-one bloats session JSON and makes downstream consumers
        (bug reports, transcripts) treat a single response as fragmented
        output. Coalescing fixes the representation without affecting the
        live streaming experience, which still yields per-chunk.
        """
        merged: list[types.Part] = []
        buf: list[str] = []

        def _flush() -> None:
            if buf:
                merged.append(types.Part.from_text(text="".join(buf)))
                buf.clear()

        for p in self._parts:
            if self._is_pure_text(p):
                buf.append(p.text)
            else:
                _flush()
                merged.append(p)
        _flush()
        return merged

    @property
    def function_calls(self) -> list[types.FunctionCall]:
        """Function call parts from the response."""
        return [p.function_call for p in self._parts if p.function_call]

    @property
    def usage_metadata(self) -> types.GenerateContentResponseUsageMetadata | None:
        return self._usage_metadata

    @property
    def grounding_metadata(self) -> types.GroundingMetadata | None:
        return self._grounding_metadata

    @property
    def finish_reason(self) -> str | None:
        return self._finish_reason
