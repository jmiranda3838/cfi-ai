from cfi_ai.planner import ExecutionPlan, format_plan
from cfi_ai.workspace import Workspace


def test_write_file_new(tmp_path):
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "new.py", "content": "print('hi')"}, workspace=ws)
    assert plan.operations[0].description == "Write to new.py (11 chars)"
    assert plan.operations[0].diff_lines is None


def test_write_file_overwrite(tmp_path):
    (tmp_path / "exist.py").write_text("old content")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "exist.py", "content": "new content"}, workspace=ws)
    assert plan.operations[0].description == "Modify exist.py"
    assert plan.operations[0].diff_lines is not None


def test_write_file_empty():
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "empty.txt", "content": ""})
    assert plan.operations[0].description == "Create empty file empty.txt"


def test_edit_file_with_diff(tmp_path):
    (tmp_path / "a.py").write_text("hello world\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("edit_file", {"path": "a.py", "old_text": "hello", "new_text": "hi"}, workspace=ws)
    assert plan.operations[0].description == "Edit a.py"
    assert plan.operations[0].diff_lines is not None


def test_format_plan_with_diff(tmp_path):
    (tmp_path / "f.txt").write_text("aaa\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "f.txt", "content": "bbb\n"}, workspace=ws)
    output = format_plan(plan)
    assert "Modify f.txt" in output
    # Diff should contain add/remove markers
    assert "[green]" in output
    assert "[red]" in output


def test_format_plan_escapes_brackets(tmp_path):
    """Rich markup characters in file content should be escaped."""
    (tmp_path / "code.py").write_text("[old_tag]\n")
    ws = Workspace(str(tmp_path))
    plan = ExecutionPlan()
    plan.add("write_file", {"path": "code.py", "content": "[new_tag]\n"}, workspace=ws)
    output = format_plan(plan)
    # The brackets should be escaped so Rich doesn't interpret them
    assert "\\[old_tag]" in output or "\\[new_tag]" in output


def test_unknown_tool():
    plan = ExecutionPlan()
    plan.add("some_tool", {"x": 1, "y": "two"})
    assert plan.operations[0].description == "Execute some_tool"
