from unittest.mock import patch

from cfi_ai.prompts.system import build_system_prompt, build_plan_mode_system_prompt, CLIENTS_SECTION
from cfi_ai.workspace import Workspace


def test_build_system_prompt():
    prompt = build_system_prompt("/home/user/project", "Workspace: /home/user/project\nContents:\n  src/")
    assert "cfi-ai" in prompt
    assert "/home/user/project" in prompt
    assert "run_command" in prompt
    assert "attach_path" in prompt
    assert "apply_patch" in prompt
    assert "write_file" in prompt
    # Old tools should not be present
    assert "list_files" not in prompt
    assert "read_file" not in prompt
    assert "search_files" not in prompt
    assert "edit_file" not in prompt
    assert "read_audio" not in prompt


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


def test_prompt_without_rg():
    with patch("cfi_ai.prompts.system.shutil.which", return_value=None):
        prompt = build_system_prompt("/tmp/test", "summary")
    assert "grep" in prompt
    # rg should not appear as a standalone command recommendation
    assert "rg" not in prompt


def test_prompt_with_rg():
    with patch("cfi_ai.prompts.system.shutil.which", return_value="/usr/local/bin/rg"):
        prompt = build_system_prompt("/tmp/test", "summary")
    assert "rg" in prompt


def test_clients_section_contains_integrate_guidance():
    assert "integrate" in CLIENTS_SECTION.lower()
    assert "rewrite the document" in CLIENTS_SECTION


def test_system_prompt_inherits_integrate_guidance(tmp_path):
    (tmp_path / "clients").mkdir()
    ws = Workspace(str(tmp_path))
    prompt = build_system_prompt(str(tmp_path), ws.summary(), workspace=ws)
    assert "rewrite the document" in prompt


def test_plan_mode_prompt_conciseness_guideline():
    prompt = build_plan_mode_system_prompt("/tmp/ws", "Test workspace.")
    assert "Do NOT include full document content" in prompt


def test_plan_mode_prompt_completeness_guideline(tmp_path):
    (tmp_path / "clients").mkdir()
    ws = Workspace(str(tmp_path))
    prompt = build_plan_mode_system_prompt(str(tmp_path), ws.summary(), workspace=ws)
    assert "ALL affected document types" in prompt
