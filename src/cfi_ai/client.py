from __future__ import annotations

import logging
import sys
import uuid
from typing import Generator

from google import genai
from google.genai import types

from cfi_ai.config import Config

_log = logging.getLogger(__name__)


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

    def stream_response(
        self,
        messages: list[types.Content],
        system: str,
        tools: types.Tool,
        *,
        mode: str = "normal",
    ) -> StreamResult:
        """Start a streaming API call. Returns a StreamResult that yields text chunks
        and provides function calls when done."""
        request_id = uuid.uuid4().hex[:8]
        max_tokens = self._max_tokens
        if mode == "map":
            # Map mode needs higher budget for multi-file writes.
            # 65536 is Gemini 2.5 Flash's max output token limit.
            max_tokens = max(max_tokens, 65536)
        _log.debug(
            "[req:%s] request mode=%s messages=%d system_len=%d model=%s max_tokens=%d",
            request_id, mode, len(messages), len(system), self._model, max_tokens,
        )
        for line in _summarize_contents(messages):
            _log.debug("[req:%s] %s", request_id, line)

        stream = self._client.models.generate_content_stream(
            model=self._model,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=[tools],
                max_output_tokens=max_tokens,
            ),
        )
        return StreamResult(stream, request_id=request_id)

    def generate_content(
        self,
        parts: list[types.Part],
        *,
        system: str | None = None,
        max_output_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        """Non-streaming API call. Returns the text response.

        If *model* is given it overrides the configured default (used by
        tools that always target a specific model like Flash).
        """
        contents = [types.Content(role="user", parts=parts)]
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_output_tokens or self._max_tokens,
        )
        response = self._client.models.generate_content(
            model=model or self._model,
            contents=contents,
            config=config,
        )
        return response.text


class StreamResult:
    """Wraps the Google Gen AI streaming response to separate text streaming from
    final part extraction."""

    def __init__(self, stream, *, request_id: str = "") -> None:
        self._stream = stream
        self._parts: list[types.Part] = []
        self._finish_reason: str | None = None
        self.request_id: str = request_id

    def text_chunks(self) -> Generator[str, None, None]:
        """Yield text delta chunks as they arrive."""
        rid = self.request_id
        buf = ""
        chunk_idx = 0
        for chunk in self._stream:
            empty_candidates = not chunk.candidates
            if empty_candidates:
                _log.debug("[req:%s] chunk %d empty_candidates=True", rid, chunk_idx)
                continue
            candidate = chunk.candidates[0]
            if candidate.finish_reason:
                self._finish_reason = candidate.finish_reason
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
        _log.debug(
            "[req:%s] stream_end total_parts=%d total_text_len=%d function_calls=%d "
            "finish_reason=%s",
            self.request_id, len(self._parts), total_text_len, fc_count,
            self._finish_reason,
        )

    @property
    def parts(self) -> list[types.Part]:
        """All accumulated parts. Available after text_chunks() is exhausted."""
        return self._parts

    @property
    def function_calls(self) -> list[types.FunctionCall]:
        """Function call parts from the response."""
        return [p.function_call for p in self._parts if p.function_call]

    @property
    def finish_reason(self) -> str | None:
        return self._finish_reason
