import pytest

from cfi_ai.workspace import Workspace
from cfi_ai.tools.edit_file import EditFileTool
from cfi_ai.tools.list_files import ListFilesTool
from cfi_ai.tools.read_file import ReadFileTool
from cfi_ai.tools.search_files import SearchFilesTool
from cfi_ai.tools.write_file import WriteFileTool
import cfi_ai.tools as tools


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("aaa")
    (tmp_path / "b.py").write_text("bbb")
    (tmp_path / "sub").mkdir()
    (tmp_path / ".git").mkdir()
    ws = Workspace(str(tmp_path))
    result = ListFilesTool().execute(ws, path=".")
    assert "a.txt" in result
    assert "b.py" in result
    assert "sub/" in result
    assert ".git" not in result


def test_list_files_recursive(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.txt").write_text("deep")
    ws = Workspace(str(tmp_path))
    result = ListFilesTool().execute(ws, path=".", recursive=True)
    assert "deep.txt" in result


def test_list_files_not_a_dir(tmp_path):
    (tmp_path / "file.txt").write_text("")
    ws = Workspace(str(tmp_path))
    result = ListFilesTool().execute(ws, path="file.txt")
    assert "not a directory" in result


def test_read_file(tmp_path):
    (tmp_path / "hello.txt").write_text("hello world")
    ws = Workspace(str(tmp_path))
    result = ReadFileTool().execute(ws, path="hello.txt")
    assert result == "hello world"


def test_read_file_not_found(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ReadFileTool().execute(ws, path="nope.txt")
    assert "not a file" in result


def test_search_files(tmp_path):
    (tmp_path / "a.py").write_text("# TODO: fix this\nprint('ok')\n")
    (tmp_path / "b.py").write_text("# nothing here\n")
    ws = Workspace(str(tmp_path))
    result = SearchFilesTool().execute(ws, pattern="TODO")
    assert "a.py:1" in result
    assert "b.py" not in result


def test_search_files_no_match(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    ws = Workspace(str(tmp_path))
    result = SearchFilesTool().execute(ws, pattern="ZZZZZ")
    assert "No matches" in result


def test_search_files_invalid_regex(tmp_path):
    ws = Workspace(str(tmp_path))
    result = SearchFilesTool().execute(ws, pattern="[invalid")
    assert "invalid regex" in result


def test_write_file(tmp_path):
    ws = Workspace(str(tmp_path))
    result = WriteFileTool().execute(ws, path="out.txt", content="hello")
    assert "Wrote 5 characters" in result
    assert (tmp_path / "out.txt").read_text() == "hello"


def test_write_file_creates_dirs(tmp_path):
    ws = Workspace(str(tmp_path))
    WriteFileTool().execute(ws, path="a/b/c.txt", content="deep")
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_edit_file(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello world')\n")
    ws = Workspace(str(tmp_path))
    result = EditFileTool().execute(ws, path="hello.py", old_text="hello world", new_text="hi")
    assert "Edited" in result
    assert (tmp_path / "hello.py").read_text() == "print('hi')\n"


def test_edit_file_not_found(tmp_path):
    ws = Workspace(str(tmp_path))
    result = EditFileTool().execute(ws, path="nope.py", old_text="x", new_text="y")
    assert "not a file" in result


def test_edit_file_old_text_missing(tmp_path):
    (tmp_path / "a.txt").write_text("abc")
    ws = Workspace(str(tmp_path))
    result = EditFileTool().execute(ws, path="a.txt", old_text="xyz", new_text="y")
    assert "not found" in result


def test_edit_file_old_text_ambiguous(tmp_path):
    (tmp_path / "a.txt").write_text("aaa")
    ws = Workspace(str(tmp_path))
    result = EditFileTool().execute(ws, path="a.txt", old_text="a", new_text="b")
    assert "3 times" in result


def test_registry():
    api_tools = tools.get_api_tools()
    names = {fd.name for fd in api_tools.function_declarations}
    assert names == {"edit_file", "list_files", "read_file", "search_files", "write_file"}


def test_is_mutating():
    assert tools.is_mutating("write_file") is True
    assert tools.is_mutating("edit_file") is True
    assert tools.is_mutating("read_file") is False
    assert tools.is_mutating("list_files") is False
    assert tools.is_mutating("search_files") is False


def test_execute_unknown():
    ws = Workspace("/tmp")
    result = tools.execute("no_such_tool", ws)
    assert "unknown tool" in result
