"""Tests for agent helper functions."""

from google.genai import types

from cfi_ai.agent import (
    _assemble_tool_result_parts,
    _build_result_slots,
    _should_retry_empty_turn,
    _split_tool_results,
)


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


class TestTurnCompletionLogic:
    """Test the structural turn-completion logic."""

    def test_empty_turn_retries_when_text_is_empty(self):
        """No tool calls + empty text -> retry while retries remain."""
        from google.genai import types

        messages = []
        continuation_retries = 0
        full_text = ""
        function_calls: list[types.FunctionCall] = []

        should_continue = False

        if _should_retry_empty_turn(function_calls, full_text, continuation_retries):
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

    def test_whitespace_only_turn_retries(self):
        """Whitespace-only text counts as an empty turn."""
        full_text = " \n\t "
        continuation_retries = 0
        function_calls: list[types.FunctionCall] = []

        assert _should_retry_empty_turn(function_calls, full_text, continuation_retries) is True

    def test_empty_turn_retries_capped(self):
        """After 2 retries, an empty turn breaks instead of retrying."""
        continuation_retries = 2
        full_text = ""
        function_calls: list[types.FunctionCall] = []

        assert _should_retry_empty_turn(function_calls, full_text, continuation_retries) is False

    def test_text_only_turn_finishes(self):
        """No tool calls + non-empty text finishes the turn."""
        full_text = "Here is the compliance report."
        function_calls: list[types.FunctionCall] = []
        continuation_retries = 0

        assert _should_retry_empty_turn(function_calls, full_text, continuation_retries) is False

    def test_text_only_turn_with_parts_still_finishes(self):
        """Text-only completion does not depend on parts being absent."""
        full_text = "Final summary"
        stream_parts = [types.Part.from_text(text=full_text)]
        function_calls: list[types.FunctionCall] = []
        continuation_retries = 0

        assert stream_parts
        assert _should_retry_empty_turn(function_calls, full_text, continuation_retries) is False

    def test_tool_calls_continue_loop_even_without_text(self):
        """Tool calls keep the loop going without triggering empty-turn retry."""
        function_calls = [types.FunctionCall(name="run_command", args={"command": "ls"})]
        full_text = ""
        continuation_retries = 0

        assert _should_retry_empty_turn(function_calls, full_text, continuation_retries) is False


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


class TestAssembleToolResultParts:
    """Tests for _assemble_tool_result_parts — the end_turn parity helper."""

    def test_flattens_in_order_no_end_turn(self):
        """Without end_turn_mixed, result parts match call count exactly."""
        slots = [
            [types.Part.from_function_response(name="write_file", response={"result": "wrote a"})],
            [types.Part.from_function_response(name="write_file", response={"result": "wrote b"})],
        ]
        parts = _assemble_tool_result_parts(slots, end_turn_mixed=False)
        assert len(parts) == 2
        assert [p.function_response.name for p in parts] == ["write_file", "write_file"]

    def test_appends_end_turn_response_when_mixed(self):
        """5 writes + end_turn in model turn -> 6 responses in user turn."""
        slots = [
            [types.Part.from_function_response(name="write_file", response={"result": f"wrote {i}"})]
            for i in range(5)
        ]
        parts = _assemble_tool_result_parts(slots, end_turn_mixed=True)
        assert len(parts) == 6
        assert parts[-1].function_response.name == "end_turn"
        assert parts[-1].function_response.response == {"result": "Turn complete."}

    def test_empty_slots_with_end_turn(self):
        """Edge case: end_turn alone via the mixed path still produces 1 part."""
        parts = _assemble_tool_result_parts([], end_turn_mixed=True)
        assert len(parts) == 1
        assert parts[0].function_response.name == "end_turn"

    def test_preserves_multi_part_slots(self):
        """Slots with multiple parts (e.g. fn_response + inline binary) flatten faithfully."""
        binary = types.Part.from_bytes(data=b"pdf", mime_type="application/pdf")
        slots = [
            [
                types.Part.from_function_response(name="attach_path", response={"result": "loaded"}),
                binary,
            ],
            [types.Part.from_function_response(name="write_file", response={"result": "wrote"})],
        ]
        parts = _assemble_tool_result_parts(slots, end_turn_mixed=True)
        # 2 parts from slot 0 + 1 from slot 1 + end_turn response
        assert len(parts) == 4
        assert parts[-1].function_response.name == "end_turn"
