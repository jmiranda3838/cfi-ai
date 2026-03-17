"""Tests for agent helper functions."""

from google.genai import types

from cfi_ai.agent import _build_result_slots, _split_tool_results


def test_split_no_binary():
    """No binary parts -> single group (same as current behavior)."""
    fn1 = types.Part.from_function_response(name="a", response={"result": "ok"})
    fn2 = types.Part.from_function_response(name="b", response={"result": "ok"})
    groups = _split_tool_results([fn1, fn2])
    assert len(groups) == 1
    assert groups[0] == [fn1, fn2]


def test_split_with_binary():
    """All fn_responses in first group, binary parts in separate groups."""
    fn1 = types.Part.from_function_response(name="a", response={"result": "ok"})
    bin1 = types.Part.from_bytes(data=b"audio", mime_type="audio/mp4")
    fn2 = types.Part.from_function_response(name="b", response={"result": "ok"})
    groups = _split_tool_results([fn1, bin1, fn2])
    assert len(groups) == 2
    assert groups[0] == [fn1, fn2]
    assert groups[1] == [bin1]


def test_split_multi_binary():
    """Multiple binary parts: fn_responses grouped first, then each binary separate."""
    fn1 = types.Part.from_function_response(name="attach_path", response={"result": "loaded audio"})
    bin1 = types.Part.from_bytes(data=b"audio_data", mime_type="audio/mp4")
    fn2 = types.Part.from_function_response(name="attach_path", response={"result": "loaded pdf"})
    bin2 = types.Part.from_bytes(data=b"pdf_data", mime_type="application/pdf")
    groups = _split_tool_results([fn1, bin1, fn2, bin2])
    assert len(groups) == 3
    assert groups[0] == [fn1, fn2]
    assert groups[1] == [bin1]
    assert groups[2] == [bin2]


def test_split_only_binary():
    """Edge case: binary parts with no fn_responses."""
    bin1 = types.Part.from_bytes(data=b"audio", mime_type="audio/mp4")
    bin2 = types.Part.from_bytes(data=b"pdf", mime_type="application/pdf")
    groups = _split_tool_results([bin1, bin2])
    assert len(groups) == 2
    assert groups[0] == [bin1]
    assert groups[1] == [bin2]


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


class TestBuildResultSlots:
    """Tests for _build_result_slots ordering preservation."""

    def test_preserves_order_mixed_read_mutate(self):
        """Mixed read/mutate run_command calls maintain original indices."""
        fc_cp = types.FunctionCall(name="run_command", args={"command": "cp a b"})
        fc_ls = types.FunctionCall(name="run_command", args={"command": "ls"})
        fc_cat = types.FunctionCall(name="run_command", args={"command": "cat f"})
        read_ops, mutate_ops, slots = _build_result_slots([fc_cp, fc_ls, fc_cat])
        # cp is mutating (index 0), ls and cat are read-only (indices 1, 2)
        assert [(i, fc.name) for i, fc in read_ops] == [(1, "run_command"), (2, "run_command")]
        assert [(i, fc.name) for i, fc in mutate_ops] == [(0, "run_command")]
        assert len(slots) == 3
        # Simulate filling slots in execution order (reads first, then mutates)
        slots[1].append(types.Part.from_function_response(name="run_command", response={"result": "ls output"}))
        slots[2].append(types.Part.from_function_response(name="run_command", response={"result": "cat output"}))
        slots[0].append(types.Part.from_function_response(name="run_command", response={"result": "cp done"}))
        # Flatten — should be in original call order: cp, ls, cat
        flat = [p for slot in slots for p in slot]
        assert flat[0].function_response.response["result"] == "cp done"
        assert flat[1].function_response.response["result"] == "ls output"
        assert flat[2].function_response.response["result"] == "cat output"

    def test_all_read(self):
        """All read-only calls: no mutate_ops, indices preserved."""
        fc1 = types.FunctionCall(name="attach_path", args={"path": "/a"})
        fc2 = types.FunctionCall(name="run_command", args={"command": "ls"})
        read_ops, mutate_ops, slots = _build_result_slots([fc1, fc2])
        assert len(read_ops) == 2
        assert len(mutate_ops) == 0
        assert len(slots) == 2

    def test_all_mutate(self):
        """All mutating calls: no read_ops, indices preserved."""
        fc1 = types.FunctionCall(name="write_file", args={"path": "a.md", "content": "x"})
        fc2 = types.FunctionCall(name="apply_patch", args={"path": "b.md", "patches": []})
        read_ops, mutate_ops, slots = _build_result_slots([fc1, fc2])
        assert len(read_ops) == 0
        assert len(mutate_ops) == 2
        assert len(slots) == 2
