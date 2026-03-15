from cfi_ai.planner import ExecutionPlan, format_plan
from cfi_ai.workspace import Workspace


def test_write_file_new(tmp_path):
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "new.py", "content": "print('hi')"}, workspace=ws)
    assert plan.operations[0].description == "Write to new.py (11 chars)"
    assert plan.operations[0].diff_lines is None


def test_write_file_empty():
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "empty.txt", "content": ""})
    assert plan.operations[0].description == "Create empty file empty.txt"


def test_apply_patch_with_diff(tmp_path):
    (tmp_path / "a.py").write_text("hello world\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("apply_patch", {
        "path": "a.py",
        "edits": [{"old_text": "hello", "new_text": "hi"}],
    }, workspace=ws)
    assert plan.operations[0].description == "Edit a.py (1 edit)"
    assert plan.operations[0].diff_lines is not None


def test_apply_patch_multiple_edits(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\ny = 2\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("apply_patch", {
        "path": "code.py",
        "edits": [
            {"old_text": "x = 1", "new_text": "x = 10"},
            {"old_text": "y = 2", "new_text": "y = 20"},
        ],
    }, workspace=ws)
    assert "2 edits" in plan.operations[0].description


def test_run_command_normal():
    plan = ExecutionPlan()
    plan.add("run_command", {"command": "mv old.txt new.txt"})
    assert plan.operations[0].description == "Run: mv old.txt new.txt"


def test_run_command_rm_labeled():
    plan = ExecutionPlan()
    plan.add("run_command", {"command": "rm temp.txt"})
    assert "[red]DELETE[/red]" in plan.operations[0].description


def test_format_plan_with_diff(tmp_path):
    (tmp_path / "f.txt").write_text("aaa\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("apply_patch", {
        "path": "f.txt",
        "edits": [{"old_text": "aaa", "new_text": "bbb"}],
    }, workspace=ws)
    output = format_plan(plan)
    assert "Edit f.txt" in output
    # Diff should contain add/remove markers
    assert "[green]" in output
    assert "[red]" in output


def test_format_plan_escapes_brackets(tmp_path):
    """Rich markup characters in file content should be escaped."""
    (tmp_path / "code.py").write_text("[old_tag]\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("apply_patch", {
        "path": "code.py",
        "edits": [{"old_text": "[old_tag]", "new_text": "[new_tag]"}],
    }, workspace=ws)
    output = format_plan(plan)
    # The brackets should be escaped so Rich doesn't interpret them
    assert "\\[old_tag]" in output or "\\[new_tag]" in output


def test_apply_patch_replace_all_diff(tmp_path):
    (tmp_path / "names.md").write_text("Hello Bristol.\nBristol is nice.\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("apply_patch", {
        "path": "names.md",
        "edits": [{"old_text": "Bristol", "new_text": "Bath", "replace_all": True}],
    }, workspace=ws)
    diff = plan.operations[0].diff_lines
    assert diff is not None
    diff_text = "".join(diff)
    assert "Bath" in diff_text
    assert "Bristol" in diff_text  # appears in the removed lines


def test_unknown_tool():
    plan = ExecutionPlan()
    plan.add("some_tool", {"x": 1, "y": "two"})
    assert plan.operations[0].description == "Execute some_tool"
