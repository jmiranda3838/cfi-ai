import pytest

from cfi_ai.tools.apply_patch import ApplyPatchTool
from cfi_ai.workspace import Workspace


def test_single_edit(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello world')\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="hello.py",
        edits=[{"old_text": "hello world", "new_text": "hi"}],
    )
    assert "Applied 1 edit" in result
    assert (tmp_path / "hello.py").read_text() == "print('hi')\n"


def test_multiple_edits(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\ny = 2\nz = 3\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="code.py",
        edits=[
            {"old_text": "x = 1", "new_text": "x = 10"},
            {"old_text": "z = 3", "new_text": "z = 30"},
        ],
    )
    assert "Applied 2 edits" in result
    assert (tmp_path / "code.py").read_text() == "x = 10\ny = 2\nz = 30\n"


def test_sequential_edits_see_previous(tmp_path):
    """Later edits see the result of earlier ones."""
    (tmp_path / "f.txt").write_text("aaa bbb ccc\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[
            {"old_text": "aaa", "new_text": "xxx"},
            {"old_text": "xxx bbb", "new_text": "yyy"},
        ],
    )
    assert "Applied 2 edits" in result
    assert (tmp_path / "f.txt").read_text() == "yyy ccc\n"


def test_transactional_no_write_on_failure(tmp_path):
    """If any edit fails, no changes are written."""
    (tmp_path / "f.txt").write_text("original content\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[
            {"old_text": "original", "new_text": "modified"},
            {"old_text": "not_here", "new_text": "fail"},
        ],
    )
    assert "Error" in result
    assert "edit 1" in result
    # File unchanged
    assert (tmp_path / "f.txt").read_text() == "original content\n"


def test_old_text_not_found(tmp_path):
    (tmp_path / "f.txt").write_text("abc")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[{"old_text": "xyz", "new_text": "new"}],
    )
    assert "not found" in result


def test_old_text_ambiguous(tmp_path):
    (tmp_path / "f.txt").write_text("aaa aaa aaa")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[{"old_text": "aaa", "new_text": "bbb"}],
    )
    assert "3 times" in result


def test_file_not_found(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="nope.py",
        edits=[{"old_text": "x", "new_text": "y"}],
    )
    assert "not a file" in result


def test_empty_edits(tmp_path):
    (tmp_path / "f.txt").write_text("abc")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(ws, path="f.txt", edits=[])
    assert "empty" in result


def test_empty_old_text(tmp_path):
    (tmp_path / "f.txt").write_text("abc")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[{"old_text": "", "new_text": "new"}],
    )
    assert "empty" in result


def test_delete_text(tmp_path):
    """new_text can be empty to delete text."""
    (tmp_path / "f.txt").write_text("hello world\n")
    ws = Workspace(str(tmp_path))
    result = ApplyPatchTool().execute(
        ws, path="f.txt",
        edits=[{"old_text": " world", "new_text": ""}],
    )
    assert "Applied 1 edit" in result
    assert (tmp_path / "f.txt").read_text() == "hello\n"
