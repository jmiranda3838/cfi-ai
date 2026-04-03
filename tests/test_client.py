"""Tests for repetition detection in StreamResult."""

from unittest.mock import MagicMock

import pytest

from cfi_ai.client import (
    StreamResult,
    _is_repeated_suffix,
    _is_degenerate_run,
    _REPEAT_BLOCK_SIZES,
    _REPEAT_MIN_TEXT_LENGTH,
    _DEGENERATE_RUN_LENGTH,
)


def test_detect_repetition_consecutive_suffix():
    """Same 500-char block back-to-back triggers detection."""
    block = "x" * _REPEAT_BLOCK_SIZES[1]
    text = "preamble " + block + block
    assert _is_repeated_suffix(text)


def test_detect_repetition_short_block():
    """Same 200-char block back-to-back triggers detection."""
    block = "y" * _REPEAT_BLOCK_SIZES[0]
    text = "preamble " + block + block
    assert _is_repeated_suffix(text)


def test_detect_repetition_false_short():
    """Text shorter than two full blocks (smallest size) cannot trigger."""
    block = "a" * (_REPEAT_BLOCK_SIZES[0] - 1)
    text = "x" + block + block  # one char short of two full smallest blocks
    assert not _is_repeated_suffix(text)


def test_detect_repetition_false_unique():
    """Long unique text should not trigger."""
    # Build text longer than the minimum threshold, but with no repeats.
    text = "".join(chr(65 + (i % 26)) for i in range(_REPEAT_MIN_TEXT_LENGTH + _REPEAT_BLOCK_SIZES[1]))
    assert not _is_repeated_suffix(text)


def test_detect_repetition_false_non_consecutive():
    """Same block appears twice but separated by different content — no trigger."""
    # Use varied content so sub-blocks don't accidentally match at smaller sizes.
    block = "".join(chr(65 + (i % 26)) for i in range(_REPEAT_BLOCK_SIZES[1]))
    separator = "".join(chr(97 + (i % 26)) for i in range(_REPEAT_BLOCK_SIZES[1]))
    text = block + separator + block
    # The last block matches text[-500:], but the preceding 500 chars are separator.
    assert not _is_repeated_suffix(text)


def _make_stream_chunks(texts: list[str]):
    """Build a fake streaming response from a list of text strings."""
    chunks = []
    for t in texts:
        part = MagicMock()
        part.text = t
        part.function_call = None
        candidate = MagicMock()
        candidate.finish_reason = None
        candidate.content.parts = [part]
        chunk = MagicMock()
        chunk.candidates = [candidate]
        chunks.append(chunk)
    return iter(chunks)


def test_text_chunks_stops_on_repetition():
    """Mock stream with repetitive chunks — verify early stop."""
    block = "Z" * _REPEAT_BLOCK_SIZES[1]
    # Build enough preamble to pass the minimum-text threshold, then repeat.
    preamble = "A" * (_REPEAT_MIN_TEXT_LENGTH - _REPEAT_BLOCK_SIZES[1])
    texts = [preamble, block, block, "this should not appear"]

    stream = _make_stream_chunks(texts)
    sr = StreamResult(stream)
    collected = list(sr.text_chunks())

    assert sr.repetition_detected is True
    # The last chunk ("this should not appear") must not have been yielded.
    assert "this should not appear" not in "".join(collected)


# --- Degenerate run detection tests ---


def test_degenerate_run_single_char():
    assert _is_degenerate_run("0" * _DEGENERATE_RUN_LENGTH)


def test_degenerate_run_with_preamble():
    assert _is_degenerate_run("915" + "0" * _DEGENERATE_RUN_LENGTH)


def test_degenerate_run_false_short():
    assert not _is_degenerate_run("0" * (_DEGENERATE_RUN_LENGTH - 1))


def test_degenerate_run_false_varied():
    text = "a" * 75 + "b" * 75
    assert not _is_degenerate_run(text)


def test_text_chunks_stops_on_degenerate_run():
    """Degenerate single-char run triggers early stop before 2000-char threshold."""
    texts = ["915", "0" * 200, "this should not appear"]
    stream = _make_stream_chunks(texts)
    sr = StreamResult(stream)
    collected = list(sr.text_chunks())
    assert sr.repetition_detected is True
    assert "this should not appear" not in "".join(collected)


# --- Map mode max_output_tokens tests ---


def test_map_mode_raises_max_tokens():
    """Map mode should use at least 65536 max_output_tokens."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        client.stream_response(
            messages=[], system="test", tools=MM(), mode="map"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.max_output_tokens == 65536


def test_normal_mode_keeps_configured_tokens():
    """Normal mode should use the configured max_tokens value."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        client.stream_response(
            messages=[], system="test", tools=MM(), mode="normal"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.max_output_tokens == 8192
