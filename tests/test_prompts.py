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


def test_plan_mode_prompt_clinical_identity():
    prompt = build_plan_mode_system_prompt("/workspace", "summary")
    assert "clinical documentation assistant" in prompt


def test_plan_mode_prompt_verify_before_claiming():
    prompt = build_plan_mode_system_prompt("/workspace", "summary")
    assert "never claim something is unaffected without verifying" in prompt.lower()


def test_execution_prompt_clinical_identity():
    prompt = build_system_prompt("/workspace", "summary")
    assert "clinical documentation assistant" in prompt


def test_execution_prompt_ripple_effect_guideline():
    prompt = build_system_prompt("/workspace", "summary")
    assert "search for all references" in prompt.lower()


def test_prompts_no_code_centric_language():
    plan_prompt = build_plan_mode_system_prompt("/workspace", "summary")
    exec_prompt = build_system_prompt("/workspace", "summary")
    for prompt in (plan_prompt, exec_prompt):
        assert "codebase" not in prompt
        assert "code paths" not in prompt
    assert "function names, parameter types" not in plan_prompt
    assert "function signatures" not in plan_prompt


def test_intake_file_plan_prompt_formats():
    from cfi_ai.prompts.intake import INTAKE_FILE_PLAN_PROMPT
    formatted = INTAKE_FILE_PLAN_PROMPT.format(
        date="2026-03-16",
        existing_clients="## Existing Clients\nNone.",
        file_reference="session.m4a",
    )
    assert "session.m4a" in formatted
    assert "2026-03-16" in formatted
    assert "Do NOT load" in formatted
    assert "placeholder client-id" in formatted
    assert "{date}" not in formatted
    assert "{file_reference}" not in formatted
