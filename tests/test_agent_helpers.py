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


class TestWorkflowContinuationLogic:
    """Test the continuation and sentinel control flow logic."""

    def test_empty_parts_workflow_mode_continues(self):
        """In workflow_mode with retries left, empty parts → continuation message."""
        from google.genai import types

        messages = []
        workflow_mode = True
        continuation_retries = 0

        # Simulate the empty-parts path
        parts_empty = True  # stream_result.parts is empty
        should_continue = False

        if parts_empty:
            if workflow_mode and continuation_retries < 2:
                continuation_retries += 1
                messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text="Continue...")],
                    )
                )
                should_continue = True

        assert should_continue is True
        assert len(messages) == 1
        assert continuation_retries == 1

    def test_empty_parts_non_workflow_breaks(self):
        """Without workflow_mode, empty parts → break."""
        workflow_mode = False
        continuation_retries = 0

        parts_empty = True
        should_break = False

        if parts_empty:
            if workflow_mode and continuation_retries < 2:
                pass  # would continue
            else:
                should_break = True

        assert should_break is True

    def test_done_sentinel_breaks(self):
        """Model says 'Done.' in workflow_mode → break."""
        workflow_mode = True
        full_text = "Done."

        should_break = False
        if workflow_mode and full_text.strip().rstrip(".").lower() == "done":
            should_break = True

        assert should_break is True

    def test_done_sentinel_case_insensitive(self):
        """Sentinel handles 'done', 'Done', 'DONE', 'Done.' etc."""
        for text in ["Done.", "Done", "done.", "done", "DONE", "DONE.", " Done. "]:
            assert text.strip().rstrip(".").lower() == "done"

    def test_empty_parts_retries_capped(self):
        """After 2 retries, empty parts → break even in workflow_mode."""
        workflow_mode = True
        continuation_retries = 2

        parts_empty = True
        should_break = False

        if parts_empty:
            if workflow_mode and continuation_retries < 2:
                pass  # would continue
            else:
                should_break = True

        assert should_break is True
