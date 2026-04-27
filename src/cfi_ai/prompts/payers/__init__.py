"""Per-payer billing/compliance rule modules — single source of truth for each payer's CPT codes, modifiers, authorization handling, and required assessment instruments. Loaded at runtime by the `load_payer_rules` tool."""

from cfi_ai.prompts.payers.aetna import AETNA_RULES
from cfi_ai.prompts.payers.evernorth import EVERNORTH_RULES
from cfi_ai.prompts.payers.optum_eap import OPTUM_EAP_RULES

PAYER_RULES: dict[str, str] = {
    "optum-eap": OPTUM_EAP_RULES,
    "aetna": AETNA_RULES,
    "evernorth": EVERNORTH_RULES,
}

VALID_PAYERS: tuple[str, ...] = tuple(PAYER_RULES.keys())
