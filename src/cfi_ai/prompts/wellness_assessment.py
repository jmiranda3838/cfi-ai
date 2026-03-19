"""Clinical prompt templates for the /wellness-assessment workflow (G22E02)."""

from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS, WA_SCORING_RULES, WA_OUTPUT_FORMAT

WA_WORKFLOW_PROMPT = (
    """\
You are processing a Wellness Assessment (Optum Form G22E02) and calculating \
structured scores. Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Input Data

Administration type: **{admin_type}** (#{admin_number})

<wa_data>
{wa_input}
</wa_data>

## Client Context

Client ID: `{client_id}`

{client_context}

## Previous Assessments

{wa_history}

"""
    + WA_SCORING_RULES
    + """
## Workflow

### Phase 1: Score & Summarize
1. Extract all item responses from the input data.
2. Calculate the GD score (sum items 1-15).
3. Determine severity level.
4. If initial administration: calculate CAGE-AID score (items 22-24).
5. **State** the scores in 1-2 sentences (e.g., "GD = 28/45 (Severe); CAGE-AID = 0/3 \
(Negative)"), then **immediately proceed to Phase 2 tool calls in the same response**.

If any item responses are ambiguous or unclear, list the specific items and ask the \
clinician to confirm before proceeding.

### Phase 2: Write File
6. Call `write_file` to create:
   - `wellness-assessments/{date}-wellness-assessment.md`

Save the file under `clients/{client_id}/`.

"""
    + WA_OUTPUT_FORMAT
    + "\n"
)

WA_FILE_WORKFLOW_PROMPT = (
    """\
You are processing a Wellness Assessment (Optum Form G22E02) and calculating \
structured scores. Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Input

Administration type: **{admin_type}** (#{admin_number})

The user wants to process a Wellness Assessment from a file. The input is: \
`{file_reference}`

Extract the file path from the input. Use the appropriate tool:
- **PDF files** (.pdf): call `extract_document(path=...)` to extract text/data
- **Image files** (.jpg, .png, .heic, etc.): call `attach_path(path=...)` to load
- **Other files**: call `attach_path(path=...)` to load into context

If the path contains shell escape characters (backslashes before spaces, quotes, \
etc.), interpret them as a shell would.

## Client Context

Client ID: `{client_id}`

{client_context}

## Previous Assessments

{wa_history}

"""
    + WA_SCORING_RULES
    + """
## Workflow

### Phase 1: Process File, Score & Summarize
1. Load the file using the appropriate tool.
2. Extract all item responses from the form.
3. Calculate the GD score (sum items 1-15).
4. Determine severity level.
5. If initial administration: calculate CAGE-AID score (items 22-24).
6. **State** the scores in 1-2 sentences, then **immediately proceed to Phase 2 \
tool calls in the same response**.

If any item responses are ambiguous or unclear from the extracted data, list the \
specific items and ask the clinician to confirm before proceeding.

### Phase 2: Write File
7. Call `write_file` to create:
   - `wellness-assessments/{date}-wellness-assessment.md`

Save the file under `clients/{client_id}/`.

"""
    + WA_OUTPUT_FORMAT
    + "\n"
)
