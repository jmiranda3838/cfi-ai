import pytest

from cfi_ai.workspace import Workspace
from cfi_ai.tools.apply_patch import ApplyPatchTool
from cfi_ai.tools.attach_path import AttachPathTool
from cfi_ai.tools.run_command import RunCommandTool
from cfi_ai.tools.write_file import WriteFileTool
import cfi_ai.tools as tools


def test_write_file(tmp_path):
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, path="out.txt", content="hello")
    assert "Wrote 5 characters" in result
    assert (tmp_path / "out.txt").read_text() == "hello"


def test_write_file_creates_dirs(tmp_path):
    ws = Workspace(str(tmp_path))
    WriteFileTool().execute(ws, path="a/b/c.txt", content="deep")
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_write_file_rejects_overwrite(tmp_path):
    (tmp_path / "exist.txt").write_text("original")
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, path="exist.txt", content="new")
    assert "already exists" in result
    assert "apply_patch" in result
    # File unchanged
    assert (tmp_path / "exist.txt").read_text() == "original"


def test_registry():
    api_tools = tools.get_api_tools()
    names = {fd.name for fd in api_tools.function_declarations}
    assert names == {"activate_map", "apply_patch", "attach_path", "end_turn", "extract_document", "interview", "run_command", "write_file"}


def test_end_turn_in_readonly_tools():
    readonly = tools.get_readonly_api_tools()
    names = {fd.name for fd in readonly.function_declarations}
    assert "end_turn" in names


def test_end_turn_not_mutating():
    assert tools.classify_mutation("end_turn", {}) is False


def test_classify_mutation_static():
    assert tools.classify_mutation("write_file", {}) is True
    assert tools.classify_mutation("apply_patch", {}) is True
    assert tools.classify_mutation("attach_path", {}) is False
    assert tools.classify_mutation("interview", {}) is False


def test_classify_mutation_run_command():
    assert tools.classify_mutation("run_command", {"command": "ls -la"}) is False
    assert tools.classify_mutation("run_command", {"command": "cat file.txt"}) is False
    assert tools.classify_mutation("run_command", {"command": "rm file.txt"}) is True
    assert tools.classify_mutation("run_command", {"command": "mv a b"}) is True
    assert tools.classify_mutation("run_command", {"command": "mkdir newdir"}) is True


def test_apply_patch_replace_all(tmp_path):
    (tmp_path / "doc.md").write_text(
        "Bristol is great.\nI love Bristol.\nBristol rocks.\nMore Bristol.\nBristol!\n"
    )
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws,
        path="doc.md",
        edits=[{"old_text": "Bristol", "new_text": "Bath", "replace_all": True}],
    )
    assert "5 replacements" in result
    content = (tmp_path / "doc.md").read_text()
    assert "Bristol" not in content
    assert content.count("Bath") == 5


def test_apply_patch_replace_all_zero_matches(tmp_path):
    (tmp_path / "doc.md").write_text("Nothing here.\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws,
        path="doc.md",
        edits=[{"old_text": "Bristol", "new_text": "Bath", "replace_all": True}],
    )
    assert "Error" in result
    assert "not found" in result


def test_apply_patch_no_replace_all_multiple_matches(tmp_path):
    (tmp_path / "doc.md").write_text("foo bar foo\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws,
        path="doc.md",
        edits=[{"old_text": "foo", "new_text": "baz"}],
    )
    assert "Error" in result
    assert "appears 2 times" in result
    # File unchanged
    assert (tmp_path / "doc.md").read_text() == "foo bar foo\n"


def test_execute_unknown():
    ws = Workspace("/tmp")
    result = tools.execute("no_such_tool", ws)
    assert "unknown tool" in result
