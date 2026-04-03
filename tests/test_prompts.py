from unittest.mock import patch

from cfi_ai.prompts.system import build_system_prompt, build_plan_mode_system_prompt, CLIENTS_SECTION
from cfi_ai.workspace import Workspace

import re


def _assert_no_unreplaced_placeholders(text: str) -> None:
    """Fail if any {placeholder} remains after .format()."""
    match = re.search(r'\{[a-z_][a-z0-9_]*\}', text)
    assert match is None, f"Unreplaced placeholder: {match.group()}"


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


def test_intake_map_prompt_formats():
    """INTAKE_MAP_PROMPT assembles without unreplaced placeholders."""
    from cfi_ai.prompts.intake import INTAKE_MAP_PROMPT
    result = INTAKE_MAP_PROMPT.format(
        transcript="Test transcript", date="2026-03-18", existing_clients="None.",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "Risk Assessment" in result
    assert "as described above" not in result


def test_intake_file_map_prompt_formats():
    from cfi_ai.prompts.intake import INTAKE_FILE_MAP_PROMPT
    result = INTAKE_FILE_MAP_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", existing_clients="None.",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "Diagnostic Impressions" in result
    assert "GD Score" in result


def test_intake_file_plan_prompt_formats():
    """Updated with stronger assertions."""
    from cfi_ai.prompts.intake import INTAKE_FILE_PLAN_PROMPT
    result = INTAKE_FILE_PLAN_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", existing_clients="None.",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "Initial Assessment" in result
    assert "current.md" in result


def test_session_map_prompt_formats():
    from cfi_ai.prompts.session import PROGRESS_NOTE_GUIDANCE, SESSION_MAP_PROMPT
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_MAP_PROMPT.format(
        transcript="Test", date="2026-03-18", client_id="jane-doe",
        client_context="Context.", progress_note_guidance=note_guidance,
    )
    _assert_no_unreplaced_placeholders(result)
    assert "DAP" in result


def test_session_file_map_prompt_formats():
    from cfi_ai.prompts.session import PROGRESS_NOTE_GUIDANCE, SESSION_FILE_MAP_PROMPT
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_FILE_MAP_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", client_id="jane-doe",
        client_context="Context.", progress_note_guidance=note_guidance,
    )
    _assert_no_unreplaced_placeholders(result)
    assert "transcribe_audio" in result


def test_session_file_plan_prompt_formats():
    from cfi_ai.prompts.session import (
        SESSION_FILE_PLAN_PROMPT, PROGRESS_NOTE_GUIDANCE, PROGRESS_NOTE_PLAN_CRITERIA,
    )
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_FILE_PLAN_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", client_id="jane-doe",
        client_context="Context.", progress_note_guidance=note_guidance,
        progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
    )
    _assert_no_unreplaced_placeholders(result)


def test_wa_map_prompt_formats():
    from cfi_ai.prompts.wellness_assessment import WA_MAP_PROMPT
    result = WA_MAP_PROMPT.format(
        date="2026-03-18", client_id="jane-doe", client_context="Context.",
        wa_history="None.", admin_type="Initial", admin_number=1, wa_input="test data",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "0-45" in result


def test_wa_file_map_prompt_formats():
    from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT
    result = WA_FILE_MAP_PROMPT.format(
        date="2026-03-18", client_id="jane-doe", client_context="Context.",
        wa_history="None.", admin_type="Re-administration", admin_number=2,
        file_reference="wa.pdf",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "extract_document" in result


def test_shared_constants_importable():
    """All shared constants exist and are non-empty strings."""
    from cfi_ai.prompts.shared import (
        CRITICAL_INSTRUCTIONS,
        INITIAL_ASSESSMENT_GUIDANCE,
        INITIAL_ASSESSMENT_GUIDANCE_FILE,
        TREATMENT_PLAN_GUIDANCE,
        INTAKE_PROGRESS_NOTE_GUIDANCE,
        CLIENT_PROFILE_GUIDANCE,
        WA_SCORING_RULES,
        WA_OUTPUT_FORMAT,
    )
    for const in (
        CRITICAL_INSTRUCTIONS, INITIAL_ASSESSMENT_GUIDANCE,
        INITIAL_ASSESSMENT_GUIDANCE_FILE,
        TREATMENT_PLAN_GUIDANCE, INTAKE_PROGRESS_NOTE_GUIDANCE,
        CLIENT_PROFILE_GUIDANCE, WA_SCORING_RULES, WA_OUTPUT_FORMAT,
    ):
        assert isinstance(const, str) and len(const) > 50


def test_critical_instructions_in_all_map_prompts():
    """CRITICAL_INSTRUCTIONS text appears in all 6 map prompts."""
    from cfi_ai.prompts.intake import INTAKE_FILE_MAP_PROMPT, INTAKE_MAP_PROMPT
    from cfi_ai.prompts.session import SESSION_FILE_MAP_PROMPT, SESSION_MAP_PROMPT
    from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT, WA_MAP_PROMPT
    marker = "Do NOT narrate the map"
    for prompt in (INTAKE_MAP_PROMPT, INTAKE_FILE_MAP_PROMPT,
                   SESSION_MAP_PROMPT, SESSION_FILE_MAP_PROMPT,
                   WA_MAP_PROMPT, WA_FILE_MAP_PROMPT):
        assert marker in prompt


def test_cage_aid_only_in_file_map():
    """CAGE-AID risk note only in file map, not transcript map."""
    from cfi_ai.prompts.intake import INTAKE_FILE_MAP_PROMPT, INTAKE_MAP_PROMPT
    assert "CAGE screen" not in INTAKE_MAP_PROMPT
    assert "CAGE screen" in INTAKE_FILE_MAP_PROMPT


def test_interview_in_system_prompts():
    """interview tool is referenced in both normal and plan mode system prompts."""
    normal = build_system_prompt("/workspace", "summary")
    plan = build_plan_mode_system_prompt("/workspace", "summary")
    assert "interview" in normal
    assert "interview" in plan


def test_interview_in_wellness_assessment_prompts():
    """Wellness assessment prompts reference interview tool for ambiguous items."""
    from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT, WA_MAP_PROMPT
    for prompt in (WA_MAP_PROMPT, WA_FILE_MAP_PROMPT):
        assert "interview tool" in prompt


def test_map_instruction_in_maps_section():
    """MAPS_SECTION contains the [MAP: ...] handling instruction."""
    from cfi_ai.prompts.system import MAPS_SECTION
    assert "[MAP:" in MAPS_SECTION
    assert "activate_map" in MAPS_SECTION
    assert 'source="implicit"' in MAPS_SECTION
