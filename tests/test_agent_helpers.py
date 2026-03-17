"""Tests for agent helper functions."""

from google.genai import types

from cfi_ai.agent import _split_tool_results


def test_split_no_binary():
    """No binary parts -> single group (same as current behavior)."""
    fn1 = types.Part.from_function_response(name="a", response={"result": "ok"})
    fn2 = types.Part.from_function_response(name="b", response={"result": "ok"})
    groups = _split_tool_results([fn1, fn2])
    assert len(groups) == 1
    assert groups[0] == [fn1, fn2]


def test_split_with_binary():
    """Binary parts get their own groups, preserving order."""
    fn1 = types.Part.from_function_response(name="a", response={"result": "ok"})
    bin1 = types.Part.from_bytes(data=b"audio", mime_type="audio/mp4")
    fn2 = types.Part.from_function_response(name="b", response={"result": "ok"})
    groups = _split_tool_results([fn1, bin1, fn2])
    assert len(groups) == 3
    assert groups[0] == [fn1]
    assert groups[1] == [bin1]
    assert groups[2] == [fn2]


def test_split_single_binary():
    """Common case: one fn_response + one binary."""
    fn = types.Part.from_function_response(name="attach_path", response={"result": "ok"})
    binary = types.Part.from_bytes(data=b"data", mime_type="audio/mp4")
    groups = _split_tool_results([fn, binary])
    assert len(groups) == 2
    assert groups[0] == [fn]
    assert groups[1] == [binary]
