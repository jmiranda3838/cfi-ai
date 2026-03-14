from cfi_ai.prompts.system import build_system_prompt
from cfi_ai.workspace import Workspace


def test_build_system_prompt():
    prompt = build_system_prompt("/home/user/project", "Workspace: /home/user/project\nContents:\n  src/")
    assert "cfi-ai" in prompt
    assert "/home/user/project" in prompt
    assert "list_files" in prompt
    assert "read_file" in prompt
    assert "write_file" in prompt
    assert "search_files" in prompt
    assert "edit_file" in prompt
    assert "read_audio" in prompt
    assert "run_command" not in prompt


def test_prompt_includes_workspace_summary():
    summary = "Workspace: /tmp/test\nContents:\n  foo.py\n  bar.js\nDetected project type(s): Python (pyproject.toml)"
    prompt = build_system_prompt("/tmp/test", summary)
    assert "foo.py" in prompt
    assert "Python" in prompt


def test_prompt_includes_clients_section_when_dir_exists(tmp_path):
    (tmp_path / "clients").mkdir()
    ws = Workspace(str(tmp_path))
    prompt = build_system_prompt(str(tmp_path), ws.summary(), workspace=ws)
    assert "Client File Structure" in prompt
    assert "/intake" in prompt


def test_prompt_excludes_clients_section_when_no_dir(tmp_path):
    ws = Workspace(str(tmp_path))
    prompt = build_system_prompt(str(tmp_path), ws.summary(), workspace=ws)
    assert "Client File Structure" not in prompt


def test_prompt_excludes_clients_section_when_no_workspace():
    prompt = build_system_prompt("/tmp/test", "summary")
    assert "Client File Structure" not in prompt
