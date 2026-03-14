from __future__ import annotations

import sys
from typing import Generator

from google import genai
from google.genai import types

from cfi_ai.config import Config


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

    def text_chunks(self) -> Generator[str, None, None]:
        """Yield text delta chunks as they arrive."""
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
                    yield part.text

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
