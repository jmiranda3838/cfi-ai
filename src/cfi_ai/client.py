from __future__ import annotations

import logging
import sys
from typing import Generator

from google import genai
from google.genai import types

from cfi_ai.config import Config

_log = logging.getLogger(__name__)

# Repetition detection constants
_REPEAT_BLOCK_SIZES = (200, 500)
_REPEAT_MIN_TEXT_LENGTH = 2000
_REPEAT_CHECK_INTERVAL = 500


def _is_repeated_suffix(text: str) -> bool:
    """Return True if the last block of *text* appears consecutively for any
    of the configured block sizes."""
    for block_size in _REPEAT_BLOCK_SIZES:
        if len(text) < block_size * 2:
            continue
        if text[-block_size:] == text[-block_size * 2 : -block_size]:
            return True
    return False


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
    ) -> StreamResult:
        """Start a streaming API call. Returns a StreamResult that yields text chunks
        and provides function calls when done."""
        stream = self._client.models.generate_content_stream(
            model=self._model,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=[tools],
                max_output_tokens=self._max_tokens,
            ),
        )
        return StreamResult(stream)


class StreamResult:
    """Wraps the Google Gen AI streaming response to separate text streaming from
    final part extraction."""

    def __init__(self, stream) -> None:
        self._stream = stream
        self._parts: list[types.Part] = []
        self._finish_reason: str | None = None
        self._repetition_detected: bool = False

    def text_chunks(self) -> Generator[str, None, None]:
        """Yield text delta chunks as they arrive."""
        buf = ""
        last_check_len = 0
        chunk_idx = 0
        for chunk in self._stream:
            if not chunk.candidates:
                continue
            candidate = chunk.candidates[0]
            if candidate.finish_reason:
                self._finish_reason = candidate.finish_reason
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                self._parts.append(part)
                if part.text:
                    _log.debug(
                        "chunk %d len=%d text=%r",
                        chunk_idx,
                        len(part.text),
                        part.text[:80],
                    )
                    chunk_idx += 1
                    buf += part.text
                    # Check for repetition once we have enough text
                    if (
                        len(buf) >= _REPEAT_MIN_TEXT_LENGTH
                        and len(buf) - last_check_len >= _REPEAT_CHECK_INTERVAL
                    ):
                        last_check_len = len(buf)
                        if _is_repeated_suffix(buf):
                            _log.warning(
                                "Repetition detected at %d chars", len(buf)
                            )
                            self._repetition_detected = True
                            return
                    yield part.text

    @property
    def repetition_detected(self) -> bool:
        return self._repetition_detected

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
