from unittest.mock import patch

from cfi_ai.prompts.system import build_system_prompt

import re


def _assert_no_unreplaced_placeholders(text: str) -> None:
    """Fail if any {placeholder} remains after .format()."""
    match = re.search(r'\{[a-z_][a-z0-9_]*\}', text)
    assert match is None, f"Unreplaced placeholder: {match.group()}"


def test_build_system_prompt():
    prompt = build_system_prompt("Workspace: /home/user/project\nContents:\n  src/")
    assert "cfi-ai" in prompt
    assert "/home/user/project" in prompt
    assert "run_command" in prompt
    assert "attach_path" in prompt
    assert "apply_patch" in prompt
    assert "write_file" in prompt
    assert "end_turn" in prompt
    # Old tools should not be present
    assert "list_files" not in prompt
    assert "read_file" not in prompt
    assert "search_files" not in prompt
    assert "edit_file" not in prompt
    assert "read_audio" not in prompt


def test_prompt_includes_workspace_summary():
    summary = "Workspace: /tmp/test\nContents:\n  foo.py\n  bar.js\nDetected project type(s): Python (pyproject.toml)"
    prompt = build_system_prompt(summary)
    assert "foo.py" in prompt
    assert "Python" in prompt


def test_prompt_includes_clients_section():
    prompt = build_system_prompt("summary")
    assert "Client File Structure" in prompt
    assert "/intake" in prompt


def test_prompt_without_rg():
    with patch("cfi_ai.prompts.system.shutil.which", return_value=None):
        prompt = build_system_prompt("summary")
    assert "grep" in prompt
    # rg should not appear as a standalone command recommendation
    # (word-boundary check — substrings like "organize" legitimately contain "rg")
    assert not re.search(r"\brg\b", prompt)


def test_prompt_with_rg():
    with patch("cfi_ai.prompts.system.shutil.which", return_value="/usr/local/bin/rg"):
        prompt = build_system_prompt("summary")
    assert "rg" in prompt


def test_clients_section_contains_integrate_guidance():
    prompt = build_system_prompt("summary")
    assert "integrate" in prompt.lower()
    assert "rewrite the document" in prompt


def test_prompts_no_narrate_guideline():
    exec_prompt = build_system_prompt("summary")
    assert "do not narrate" in exec_prompt


def test_execution_prompt_clinical_identity():
    prompt = build_system_prompt("summary")
    assert "clinical documentation assistant" in prompt


def test_execution_prompt_ripple_effect_guideline():
    prompt = build_system_prompt("summary")
    assert "search for all references" in prompt.lower()


def test_prompts_no_code_centric_language():
    exec_prompt = build_system_prompt("summary")
    assert "codebase" not in exec_prompt
    assert "code paths" not in exec_prompt


# --- Clinical map prompt rendering ---

def test_intake_prompt_formats():
    """INTAKE_PROMPT assembles without unreplaced placeholders."""
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    result = INTAKE_PROMPT.format(date="2026-03-18")
    _assert_no_unreplaced_placeholders(result)
    assert "Risk Assessment" in result
    assert "Diagnostic Impressions" in result
    assert "current.md" not in result


def test_session_map_prompt_formats():
    from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date="2026-03-18")
    result = SESSION_MAP_PROMPT.format(
        date="2026-03-18",
        progress_note_guidance=note_guidance,
    )
    _assert_no_unreplaced_placeholders(result)
    assert "TheraNest Form: Progress Note" in result
    assert "run_command ls" in result
    # Single consolidated prompt handles both file and non-file inputs
    assert "attach_path" in result


def test_compliance_prompt_formats():
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    result = COMPLIANCE_PROMPT.format(date="2026-03-18")
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
    result = TP_REVIEW_PROMPT.format(date="2026-03-18")
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


def test_per_document_constants_importable():
    """Each per-document module exposes its constants as non-empty strings."""
    from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS
    from cfi_ai.prompts.narrative_therapy import NARRATIVE_THERAPY_ORIENTATION
    from cfi_ai.prompts.initial_assessment import INITIAL_ASSESSMENT_TEMPLATE
    from cfi_ai.prompts.treatment_plan import (
        THERANEST_INTERVENTIONS,
        TREATMENT_PLAN_GUIDANCE,
    )
    from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
    from cfi_ai.prompts.client_profile import CLIENT_PROFILE_GUIDANCE
    from cfi_ai.prompts.payers.optum_eap import WA_SCORING_RULES, WA_OUTPUT_FORMAT
    for const in (
        CRITICAL_INSTRUCTIONS,
        NARRATIVE_THERAPY_ORIENTATION,
        INITIAL_ASSESSMENT_TEMPLATE,
        THERANEST_INTERVENTIONS, TREATMENT_PLAN_GUIDANCE,
        PROGRESS_NOTE_GUIDANCE,
        CLIENT_PROFILE_GUIDANCE, WA_SCORING_RULES, WA_OUTPUT_FORMAT,
    ):
        assert isinstance(const, str) and len(const) > 50


def test_map_prompts_have_reference_loading_wrapper():
    """All clinical map prompts must clarify that loading != executing."""
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

    marker = "Loading the map does not mean you must execute the workflow"
    for name, prompt in [
        ("INTAKE_PROMPT", INTAKE_PROMPT),
        ("SESSION_MAP_PROMPT", SESSION_MAP_PROMPT),
        ("COMPLIANCE_PROMPT", COMPLIANCE_PROMPT),
        ("TP_REVIEW_PROMPT", TP_REVIEW_PROMPT),
    ]:
        assert marker in prompt, f"{name} missing reference-loading wrapper"


def test_critical_instructions_in_all_map_prompts():
    """CRITICAL_INSTRUCTIONS text appears in all clinical map prompts."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
    marker = "Do NOT narrate the map"
    for prompt in (INTAKE_PROMPT, SESSION_MAP_PROMPT,
                   COMPLIANCE_PROMPT, TP_REVIEW_PROMPT):
        assert marker in prompt


def test_documentation_principles_in_all_map_prompts():
    """DOCUMENTATION_PRINCIPLES text appears in all clinical map prompts."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
    for name, prompt in [
        ("INTAKE_PROMPT", INTAKE_PROMPT),
        ("SESSION_MAP_PROMPT", SESSION_MAP_PROMPT),
        ("COMPLIANCE_PROMPT", COMPLIANCE_PROMPT),
        ("TP_REVIEW_PROMPT", TP_REVIEW_PROMPT),
    ]:
        assert "Documentation Principles" in prompt, f"{name} missing principles header"
        assert "minimum-necessary" in prompt.lower() or "minimum necessary" in prompt.lower(), (
            f"{name} missing minimum-necessary phrasing"
        )


def test_compliance_narrows_vague_findings_to_necessity_fields():
    """Compliance auditor must scope 'vague' findings to medically-necessary elements."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    assert "Scope of \"vague\" findings" in COMPLIANCE_PROMPT
    assert "MUST NOT be flagged" in COMPLIANCE_PROMPT


def test_reference_mode_forbids_writes():
    """All clinical map prompts must explicitly forbid write_file/apply_patch in reference mode."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

    for name, prompt in [
        ("INTAKE_PROMPT", INTAKE_PROMPT),
        ("SESSION_MAP_PROMPT", SESSION_MAP_PROMPT),
        ("COMPLIANCE_PROMPT", COMPLIANCE_PROMPT),
        ("TP_REVIEW_PROMPT", TP_REVIEW_PROMPT),
    ]:
        assert "MUST NOT" in prompt, f"{name} missing reference-mode prohibition"
        assert "write_file" in prompt, f"{name} missing write_file prohibition"
        assert "apply_patch" in prompt, f"{name} missing apply_patch prohibition"


def test_maps_section_describes_missing_record_contract():
    prompt = build_system_prompt("summary")
    assert "missing or out-of-scope records may be surfaced as findings" in prompt
    assert "requires an existing treatment plan and progress notes to generate updates" in prompt


def test_interview_in_system_prompts():
    """interview tool is referenced in the system prompt."""
    normal = build_system_prompt("summary")
    assert "interview" in normal


def test_maps_section_references_slash_invocation_format():
    """System prompt tells the LLM how to recognize slash invocations."""
    prompt = build_system_prompt("summary")
    assert "activate_map" in prompt
    assert "User invoked /" in prompt


# -- TheraNest 30-field progress note form --

THERANEST_FIELD_MARKERS = [
    "Participant(s) in Session",
    "Type Of Note",
    "CPT Code Billed",
    "CPT Code Modifiers",
    "Modality",
    "Authorization Number",
    "Session # of Authorized Total",
    "Payer",
    "Diagnostic Impressions",
    "Diagnosis Addressed This Session",
    "Treatment Goals",
    "Goals/Objectives Addressed This Session",
    "Mental Status",
    "Functional Impairment",
    "Risk Assessment",
    "Risk Level",
    "Protective Factors",
    "Safety Plan",
    "Tarasoff",
    "Subjective",
    "Session Focus",
    "Planned Intervention",
    "Therapeutic Intervention",
    "Client's Response to Intervention",
    "Client Progress",
    "Medical Necessity Statement",
    "Plan",
    "Additional Notes",
]


def test_progress_note_guidance_covers_all_30_fields():
    """Ongoing-session progress note guidance must cover every TheraNest field."""
    from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
    for marker in THERANEST_FIELD_MARKERS:
        assert marker in PROGRESS_NOTE_GUIDANCE, (
            f"PROGRESS_NOTE_GUIDANCE missing field marker: {marker!r}"
        )


def test_optum_eap_rules_carry_modifier_and_cpt_validation():
    """Optum EWS/EAP modifier and CPT-code constraints live in the payer-rules module."""
    from cfi_ai.prompts.payers.optum_eap import OPTUM_EAP_RULES
    assert "HJ" in OPTUM_EAP_RULES
    assert "U5" in OPTUM_EAP_RULES
    assert "GT" in OPTUM_EAP_RULES
    assert "90834" in OPTUM_EAP_RULES
    assert "90791" in OPTUM_EAP_RULES
    assert "Optum EWS" in OPTUM_EAP_RULES


def test_client_profile_guidance_has_billing_section():
    """Client profile guidance must include the Billing & Provider section."""
    from cfi_ai.prompts.client_profile import CLIENT_PROFILE_GUIDANCE
    assert "Billing & Provider Information" in CLIENT_PROFILE_GUIDANCE
    assert "Payer" in CLIENT_PROFILE_GUIDANCE
    assert "Authorization Number" in CLIENT_PROFILE_GUIDANCE
    assert "Total Authorized Sessions" in CLIENT_PROFILE_GUIDANCE
    assert "Default Modality" in CLIENT_PROFILE_GUIDANCE
    assert "Rendering Provider" in CLIENT_PROFILE_GUIDANCE
    assert "Supervised" in CLIENT_PROFILE_GUIDANCE
    assert "Supervisor" in CLIENT_PROFILE_GUIDANCE


def test_compliance_prompt_checks_new_fields():
    """Compliance audit prompt is payer-agnostic but covers the generic TheraNest fields."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    assert "Functional Impairment" in COMPLIANCE_PROMPT
    assert "Client's Response to Intervention" in COMPLIANCE_PROMPT
    assert "Therapeutic Intervention" in COMPLIANCE_PROMPT
    assert "Authorization Number" in COMPLIANCE_PROMPT
    assert "Billing & Provider" in COMPLIANCE_PROMPT


def test_optum_eap_rules_have_intake_cpt_exception():
    """Optum EWS/EAP forbids 90791 at intake; the rule lives in the payer-rules module."""
    from cfi_ai.prompts.payers.optum_eap import OPTUM_EAP_RULES
    assert "90834" in OPTUM_EAP_RULES
    assert "Do NOT use `90791`" in OPTUM_EAP_RULES
    assert "Optum EAP intakes" in OPTUM_EAP_RULES


def test_tp_review_references_new_field_names():
    """tp-review Phase 1 must point at the new TheraNest field names."""
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
    assert "Therapeutic Intervention" in TP_REVIEW_PROMPT
    assert "Client Progress" in TP_REVIEW_PROMPT
    assert "Client's Response to Intervention" in TP_REVIEW_PROMPT
    assert "Functional Impairment" in TP_REVIEW_PROMPT


def test_session_map_phase1_backfills_billing_section():
    """Session map prompt must instruct interview-driven billing backfill."""
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    assert "Billing & Provider Information" in SESSION_MAP_PROMPT
    assert "interview" in SESSION_MAP_PROMPT
    assert "overwrite=true" in SESSION_MAP_PROMPT


# --- Multi-payer Phase 0 wiring across all four clinical maps ---


def _render_clinical_map_prompts(date: str = "2026-04-27") -> dict[str, str]:
    """Render every clinical map prompt with all required placeholders filled."""
    from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
    from cfi_ai.prompts.intake import INTAKE_PROMPT
    from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
    from cfi_ai.prompts.session import SESSION_MAP_PROMPT
    from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=date)
    return {
        "intake": INTAKE_PROMPT.format(date=date),
        "session": SESSION_MAP_PROMPT.format(
            date=date, progress_note_guidance=note_guidance
        ),
        "compliance": COMPLIANCE_PROMPT.format(date=date),
        "tp-review": TP_REVIEW_PROMPT.format(date=date),
    }


def test_clinical_maps_have_payer_resolution_step():
    """Every clinical map prompt must drive payer resolution + load_payer_rules."""
    for map_name, prompt in _render_clinical_map_prompts().items():
        assert "Resolve Payer" in prompt, f"{map_name} missing 'Resolve Payer' step"
        assert "load_payer_rules" in prompt, f"{map_name} missing load_payer_rules call"


def test_clinical_maps_have_slug_mapping_table():
    """Every clinical map prompt must spell out the Payer-field-to-slug mapping."""
    for map_name, prompt in _render_clinical_map_prompts().items():
        for slug in ("optum-eap", "aetna", "evernorth"):
            assert slug in prompt, f"{map_name} missing slug {slug!r} in payer-mapping table"
        assert "Optum EWS/EAP" in prompt, f"{map_name} missing Optum payer-name example"


def test_payer_resolution_precedes_record_loading_in_phased_maps():
    """In compliance + tp-review, payer resolution is Phase 0 (runs before record loading)."""
    for map_name in ("compliance", "tp-review"):
        prompt = _render_clinical_map_prompts()[map_name]
        # Phase 0 should come before any later phase
        phase_0_idx = prompt.find("Phase 0")
        phase_1_idx = prompt.find("Phase 1")
        assert phase_0_idx != -1, f"{map_name} missing 'Phase 0' label"
        assert phase_1_idx != -1, f"{map_name} missing 'Phase 1' label"
        assert phase_0_idx < phase_1_idx, f"{map_name} Phase 0 must precede Phase 1"


def test_assessment_instrument_logic_gated_on_payer():
    """Generic prompts must gate assessment-instrument work on the active payer's rules.

    This is the de-Optum-ization invariant: the literal strings 'G22E02',
    'Global Distress', and 'CAGE-AID' should NOT appear in the generic
    prompts (intake, session, compliance, tp-review) — they live in
    `prompts/payers/optum_eap.py` only.
    """
    for map_name, prompt in _render_clinical_map_prompts().items():
        for forbidden in ("G22E02", "Global Distress", "CAGE-AID"):
            assert forbidden not in prompt, (
                f"{map_name} contains {forbidden!r} — should be payer-conditional, "
                f"not baked into the generic prompt"
            )


def test_intake_compliance_tp_review_use_assessment_gate_phrasing():
    """Maps that touch assessment instruments must use 'active payer' gate phrasing."""
    rendered = _render_clinical_map_prompts()
    for map_name in ("intake", "compliance", "tp-review"):
        prompt = rendered[map_name]
        assert "active payer" in prompt, (
            f"{map_name} should gate assessment-instrument logic on the active payer "
            f"(missing 'active payer' phrasing)"
        )
