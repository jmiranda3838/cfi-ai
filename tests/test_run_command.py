import pytest

from cfi_ai.tools.run_command import RunCommandTool, is_command_mutating
from cfi_ai.workspace import Workspace


def test_ls(tmp_path):
    (tmp_path / "hello.txt").write_text("hi")
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls")
    assert "hello.txt" in result


def test_cat(tmp_path):
    (tmp_path / "f.txt").write_text("file content here")
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="cat f.txt")
    assert "file content here" in result


def test_pwd(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="pwd")
    assert str(tmp_path) in result


def test_disallowed_command(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="curl http://example.com")
    assert "not allowed" in result


def test_python_disallowed(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="python -c 'print(1)'")
    assert "not allowed" in result


def test_pipe_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls | grep foo")
    assert "metacharacter" in result


def test_redirect_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls > out.txt")
    assert "metacharacter" in result


def test_semicolon_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls ; rm -rf /")
    assert "metacharacter" in result


def test_and_chain_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls && cat foo")
    assert "metacharacter" in result


def test_rm_recursive_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="rm -rf .")
    assert "recursive delete" in result


def test_rm_R_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="rm -R somedir")
    assert "recursive delete" in result


def test_rm_recursive_flag_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="rm --recursive somedir")
    assert "recursive delete" in result


def test_rm_single_file(tmp_path):
    (tmp_path / "deleteme.txt").write_text("bye")
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="rm deleteme.txt")
    assert not (tmp_path / "deleteme.txt").exists()


def test_mkdir(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="mkdir newdir")
    assert (tmp_path / "newdir").is_dir()


def test_workspace_escape_rejected(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="rm ../outside.txt")
    assert "Error" in result


def test_empty_command(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="")
    assert "empty command" in result


def test_parse_error(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls 'unterminated")
    assert "Error" in result


def test_is_command_mutating_true():
    assert is_command_mutating("rm file.txt") is True
    assert is_command_mutating("mv a b") is True
    assert is_command_mutating("cp a b") is True
    assert is_command_mutating("mkdir newdir") is True


def test_is_command_mutating_false():
    assert is_command_mutating("ls -la") is False
    assert is_command_mutating("cat file.txt") is False
    assert is_command_mutating("find . -name '*.py'") is False
    assert is_command_mutating("rg TODO") is False


def test_is_command_mutating_invalid():
    assert is_command_mutating("") is False
    assert is_command_mutating("'unterminated") is False


def test_no_output(tmp_path):
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="ls")
    # empty dir — ls may produce no output or just empty
    # just ensure no crash
    assert isinstance(result, str)


def test_find_command(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.py").write_text("pass")
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="find . -name '*.py'")
    assert "deep.py" in result


def test_wc_command(tmp_path):
    (tmp_path / "lines.txt").write_text("a\nb\nc\n")
    ws = Workspace(str(tmp_path))
    result = RunCommandTool().execute(ws, command="wc -l lines.txt")
    assert "3" in result
