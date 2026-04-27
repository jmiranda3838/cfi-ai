"""Tests for the per-payer rules package (`cfi_ai.prompts.payers`)."""

from cfi_ai.prompts.payers import PAYER_RULES, VALID_PAYERS
from cfi_ai.prompts.payers.aetna import AETNA_RULES
from cfi_ai.prompts.payers.evernorth import EVERNORTH_RULES
from cfi_ai.prompts.payers.optum_eap import (
    OPTUM_EAP_RULES,
    WA_OUTPUT_FORMAT,
    WA_SCORING_RULES,
)


def test_valid_payers_tuple():
    assert VALID_PAYERS == ("optum-eap", "aetna", "evernorth")


def test_payer_rules_keys_match_valid_payers():
    assert set(PAYER_RULES) == set(VALID_PAYERS)


def test_payer_rules_values_are_non_empty_strings():
    for slug, rules in PAYER_RULES.items():
        assert isinstance(rules, str), f"{slug} rules must be a string"
        assert len(rules) > 50, f"{slug} rules suspiciously short"


def test_optum_eap_rules_contain_g22e02_scoring():
    """Optum EWS/EAP rules carry the G22E02 wellness-assessment scoring + format."""
    assert "G22E02" in OPTUM_EAP_RULES
    assert "Global Distress" in OPTUM_EAP_RULES
    assert "CAGE-AID" in OPTUM_EAP_RULES
    assert "Severity" in OPTUM_EAP_RULES


def test_optum_eap_wa_helpers_are_substrings_of_full_rules():
    """The split WA_SCORING_RULES / WA_OUTPUT_FORMAT constants are reused inside OPTUM_EAP_RULES."""
    assert WA_SCORING_RULES in OPTUM_EAP_RULES
    assert WA_OUTPUT_FORMAT in OPTUM_EAP_RULES


def test_optum_eap_rules_carry_billing_constraints():
    """Optum EWS/EAP CPT-code, modifier, and authorization rules live in the payer module."""
    assert "90834" in OPTUM_EAP_RULES
    assert "90791" in OPTUM_EAP_RULES
    assert "HJ" in OPTUM_EAP_RULES
    assert "U5" in OPTUM_EAP_RULES
    assert "Authorization" in OPTUM_EAP_RULES


def test_aetna_rules_are_stub_until_populated():
    """Aetna rules are a placeholder TODO until the practice bills its first Aetna client."""
    assert "TODO" in AETNA_RULES
    assert "Aetna" in AETNA_RULES


def test_evernorth_rules_are_stub_until_populated():
    """Evernorth rules are a placeholder TODO until the practice bills its first Evernorth client."""
    assert "TODO" in EVERNORTH_RULES
    assert "Evernorth" in EVERNORTH_RULES
