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


def test_intake_prompt_formats():
    """INTAKE_PROMPT assembles without unreplaced placeholders."""
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    result = INTAKE_PROMPT.format(
        intake_input="Test intake input", date="2026-03-18",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "Risk Assessment" in result
    assert "Diagnostic Impressions" in result
    assert "GD Score" in result
    assert "current.md" not in result


def test_intake_plan_prompt_formats():
    """INTAKE_PLAN_PROMPT assembles without unreplaced placeholders."""
    from cfi_ai.prompts.intake import INTAKE_PLAN_PROMPT
    result = INTAKE_PLAN_PROMPT.format(
        intake_input="session.m4a", date="2026-03-18",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "Initial Assessment" in result
    assert "current.md" not in result


def test_session_map_prompt_formats():
    from cfi_ai.prompts.session import PROGRESS_NOTE_GUIDANCE, SESSION_MAP_PROMPT
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_MAP_PROMPT.format(
        transcript="Test", date="2026-03-18", client_id="jane-doe",
        progress_note_guidance=note_guidance,
    )
    _assert_no_unreplaced_placeholders(result)
    assert "DAP" in result
    assert "run_command ls" in result


def test_session_file_map_prompt_formats():
    from cfi_ai.prompts.session import PROGRESS_NOTE_GUIDANCE, SESSION_FILE_MAP_PROMPT
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_FILE_MAP_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", client_id="jane-doe",
        progress_note_guidance=note_guidance,
    )
    _assert_no_unreplaced_placeholders(result)
    assert "attach_path" in result
    assert "run_command ls" in result


def test_session_file_plan_prompt_formats():
    from cfi_ai.prompts.session import (
        SESSION_FILE_PLAN_PROMPT, PROGRESS_NOTE_GUIDANCE, PROGRESS_NOTE_PLAN_CRITERIA,
    )
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_FILE_PLAN_PROMPT.format(
        file_reference="session.m4a", date="2026-03-18", client_id="jane-doe",
        progress_note_guidance=note_guidance,
        progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
    )
    _assert_no_unreplaced_placeholders(result)


def test_compliance_prompt_formats():
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    result = COMPLIANCE_PROMPT.format(date="2026-03-18", client_id="jane-doe")
    _assert_no_unreplaced_placeholders(result)
    assert "run_command ls" in result
    assert "current.md" not in result


def test_compliance_prompt_reports_missing_records_as_findings():
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT

    assert "Missing documentation is a valid audit finding" in COMPLIANCE_PROMPT
    assert "Do NOT invent cross-document comparisons" in COMPLIANCE_PROMPT
    assert "cannot be assessed" in COMPLIANCE_PROMPT
    assert "Do not infer missing clinical documentation" in COMPLIANCE_PROMPT


def test_tp_review_prompt_formats():
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
    result = TP_REVIEW_PROMPT.format(date="2026-03-18", client_id="jane-doe")
    _assert_no_unreplaced_placeholders(result)
    assert "run_command ls" in result
    assert "current.md" not in result


def test_tp_review_prompt_stops_writes_when_prereqs_missing():
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

    assert "You must have the latest treatment plan." in TP_REVIEW_PROMPT
    assert "You must have at least one progress note." in TP_REVIEW_PROMPT
    assert "Do not draft updated treatment plan files" in TP_REVIEW_PROMPT
    assert "do not call `write_file`" in TP_REVIEW_PROMPT
    assert "Do NOT fabricate treatment plan structure, missing source content, or prior clinical" in TP_REVIEW_PROMPT


def test_wa_map_prompt_formats():
    from cfi_ai.prompts.wellness_assessment import WA_MAP_PROMPT
    result = WA_MAP_PROMPT.format(
        date="2026-03-18", client_id="jane-doe", wa_input="test data",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "0-45" in result
    assert "run_command ls" in result


def test_wa_file_map_prompt_formats():
    from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT
    result = WA_FILE_MAP_PROMPT.format(
        date="2026-03-18", client_id="jane-doe",
        file_reference="wa.pdf",
    )
    _assert_no_unreplaced_placeholders(result)
    assert "extract_document" in result
    assert "run_command ls" in result


def test_shared_constants_importable():
    """All shared constants exist and are non-empty strings."""
    from cfi_ai.prompts.shared import (
        CRITICAL_INSTRUCTIONS,
        NARRATIVE_THERAPY_PRINCIPLES,
        NARRATIVE_THERAPY_PROGRESS,
        NARRATIVE_THERAPY_ORIENTATION,
        INITIAL_ASSESSMENT_GUIDANCE,
        INITIAL_ASSESSMENT_GUIDANCE_FILE,
        TREATMENT_PLAN_GUIDANCE,
        INTAKE_PROGRESS_NOTE_GUIDANCE,
        CLIENT_PROFILE_GUIDANCE,
        WA_SCORING_RULES,
        WA_OUTPUT_FORMAT,
    )
    for const in (
        CRITICAL_INSTRUCTIONS,
        NARRATIVE_THERAPY_PRINCIPLES, NARRATIVE_THERAPY_PROGRESS,
        NARRATIVE_THERAPY_ORIENTATION,
        INITIAL_ASSESSMENT_GUIDANCE,
        INITIAL_ASSESSMENT_GUIDANCE_FILE,
        TREATMENT_PLAN_GUIDANCE, INTAKE_PROGRESS_NOTE_GUIDANCE,
        CLIENT_PROFILE_GUIDANCE, WA_SCORING_RULES, WA_OUTPUT_FORMAT,
    ):
        assert isinstance(const, str) and len(const) > 50


def test_critical_instructions_in_all_map_prompts():
    """CRITICAL_INSTRUCTIONS text appears in all map prompts."""
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.session import SESSION_FILE_MAP_PROMPT, SESSION_MAP_PROMPT
    from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT, WA_MAP_PROMPT
    marker = "Do NOT narrate the map"
    for prompt in (INTAKE_PROMPT,
                   SESSION_MAP_PROMPT, SESSION_FILE_MAP_PROMPT,
                   WA_MAP_PROMPT, WA_FILE_MAP_PROMPT):
        assert marker in prompt


def test_cage_aid_in_unified_intake_prompt():
    """CAGE-AID risk note is present in the unified intake prompt."""
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    assert "CAGE screen" in INTAKE_PROMPT


def test_maps_section_describes_missing_record_contract():
    from cfi_ai.prompts.system import MAPS_SECTION

    assert "missing records may be surfaced as findings" in MAPS_SECTION
    assert "requires an existing treatment plan and progress notes to generate updates" in MAPS_SECTION


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


def test_measuring_progress_only_in_evaluation_prompts():
    """Part B (Measuring Progress) appears in compliance/tp-review but not session/intake."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
    from cfi_ai.prompts.session import PROGRESS_NOTE_GUIDANCE
    from cfi_ai.prompts.intake import INTAKE_PROMPT

    marker = "Measuring Progress in Narrative Therapy"
    # Evaluation prompts keep the rubric
    assert marker in COMPLIANCE_PROMPT
    assert marker in TP_REVIEW_PROMPT
    # Generation prompts use only core principles
    assert marker not in PROGRESS_NOTE_GUIDANCE
    assert marker not in INTAKE_PROMPT


def test_orientation_alias_equals_split():
    """Backwards-compat alias equals the two split constants combined."""
    from cfi_ai.prompts.shared import (
        NARRATIVE_THERAPY_ORIENTATION,
        NARRATIVE_THERAPY_PRINCIPLES,
        NARRATIVE_THERAPY_PROGRESS,
    )
    assert NARRATIVE_THERAPY_ORIENTATION == NARRATIVE_THERAPY_PRINCIPLES + NARRATIVE_THERAPY_PROGRESS
