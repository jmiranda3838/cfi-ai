import pytest

from cfi_ai.workspace import Workspace
from cfi_ai.tools.apply_patch import ApplyPatchTool
from cfi_ai.tools.attach_path import AttachPathTool
from cfi_ai.tools.load_form_template import LoadFormTemplateTool
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


def test_write_file_missing_path_returns_actionable_error(tmp_path):
    """Regression for issue #77 Turn 18-19: a call missing 'path' used to
    return the opaque string 'Error: path' via KeyError. It should now
    name both required args so the model can self-correct."""
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, content="hello")
    assert result.startswith("Error:")
    assert "path" in result and "content" in result
    assert "Missing: path" in result


def test_write_file_missing_content_returns_actionable_error(tmp_path):
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, path="out.txt")
    assert result.startswith("Error:")
    assert "Missing: content" in result


def test_write_file_allows_empty_content(tmp_path):
    """An empty string is a valid file body and must be accepted."""
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, path="empty.txt", content="")
    assert "Wrote 0 characters" in result
    assert (tmp_path / "empty.txt").read_text() == ""


def test_attach_path_missing_path_returns_actionable_error(tmp_path):
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws)
    assert result.startswith("Error:")
    assert "path" in result


def test_registry():
    api_tools = tools.get_api_tools()
    names = {fd.name for fd in api_tools[0].function_declarations}
    assert names == {"activate_map", "apply_patch", "attach_path", "end_turn", "extract_document", "interview", "load_form_template", "load_payer_rules", "run_command", "write_file"}


def test_load_form_template_description_describes_two_step_flow():
    description = LoadFormTemplateTool().definition().description
    assert "before drafting" in description
    assert "After this tool returns" in description
    assert "same response" not in description


def test_get_api_tools_includes_google_search():
    api_tools = tools.get_api_tools()
    assert isinstance(api_tools, list)
    assert len(api_tools) == 2
    assert api_tools[0].function_declarations
    assert api_tools[1].google_search is not None


def test_get_api_tools_excludes_google_search_when_disabled():
    api_tools = tools.get_api_tools(enable_grounding=False)
    assert isinstance(api_tools, list)
    assert len(api_tools) == 1
    assert api_tools[0].function_declarations
    # Function declarations are still present and complete; only the grounding entry is dropped.
    names = {fd.name for fd in api_tools[0].function_declarations}
    assert "write_file" in names


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
