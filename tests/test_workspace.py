import pytest
from pathlib import Path

from cfi_ai.workspace import Workspace


def test_validate_path_within(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ws.validate_path("foo/bar.txt")
    assert result == tmp_path / "foo" / "bar.txt"


def test_validate_path_escape(tmp_path):
    ws = Workspace(str(tmp_path))
    with pytest.raises(ValueError, match="escapes workspace"):
        ws.validate_path("../../etc/passwd")


def test_validate_path_dot(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ws.validate_path(".")
    assert result == tmp_path


def test_validate_path_nested(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ws.validate_path("a/b/c/d/e.txt")
    assert result == tmp_path / "a" / "b" / "c" / "d" / "e.txt"


def test_validate_path_sibling_prefix(tmp_path):
    """Sibling dir whose name starts with workspace root name must be rejected."""
    # Create a workspace at tmp_path/bar, then try to access tmp_path/bar-other
    root = tmp_path / "bar"
    root.mkdir()
    sibling = tmp_path / "bar-other"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("secret")
    ws = Workspace(str(root))
    with pytest.raises(ValueError, match="escapes workspace"):
        ws.validate_path("../bar-other/secret.txt")


def test_validate_path_absolute_escape(tmp_path):
    ws = Workspace(str(tmp_path))
    with pytest.raises(ValueError, match="escapes workspace"):
        ws.validate_path("/etc/passwd")


def test_validate_path_dot_dot_in_middle(tmp_path):
    ws = Workspace(str(tmp_path))
    with pytest.raises(ValueError, match="escapes workspace"):
        ws.validate_path("sub/../../../etc/passwd")


def test_summary_empty(tmp_path):
    ws = Workspace(str(tmp_path))
    s = ws.summary()
    assert "empty directory" in s
    assert str(tmp_path) in s


def test_summary_with_files(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')")
    (tmp_path / "subdir").mkdir()
    (tmp_path / ".hidden").write_text("")
    ws = Workspace(str(tmp_path))
    s = ws.summary()
    assert "hello.py" in s
    assert "subdir/" in s
    assert ".hidden" not in s


def test_summary_project_detection(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    ws = Workspace(str(tmp_path))
    s = ws.summary()
    assert "Python" in s
