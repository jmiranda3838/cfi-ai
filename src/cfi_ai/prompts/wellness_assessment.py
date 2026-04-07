"""Clinical prompt templates for the /wellness-assessment map (G22E02)."""

from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS, WA_SCORING_RULES, WA_OUTPUT_FORMAT

WA_MAP_PROMPT = (
    """\
You are processing a Wellness Assessment (Optum Form G22E02) and calculating \
structured scores. Today's date is {date}.

## How to Use This Map

This map contains reference information and workflow steps for scoring a G22E02 \
Wellness Assessment. Loading this map does not mean you must execute the \
workflow. The Phase blocks, "Save ALL files" instructions, and any "immediately \
proceed" directives below are the workflow — they apply only when execution is \
the intent.

- **Execution mode** — Use this when the user clearly asked you to score or \
process a wellness assessment (e.g., "score this WA," "process the G22E02," or \
any slash command that maps to this workflow). Follow the phases below in order, \
including the client-context loading steps and the file write.
- **Reference mode** — Use this when the user is asking a question, comparing \
options, or thinking through a decision related to wellness assessments. Answer \
the user's actual question using the content below as reference. You MAY still \
load specific client files with `attach_path` or `run_command` if you need them \
to answer well (e.g., to look up a prior GD score for trend context). What you \
MUST NOT do in reference mode: auto-execute the canned phase sequence, bulk-load \
every file the workflow normally touches, or call `write_file`/`apply_patch` \
unless the user explicitly confirms they want the documents produced.

When in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Input Data

<wa_data>
{wa_input}
</wa_data>

## Client Context

Client ID: `{client_id}`

Load client context and determine administration type:
1. Use `run_command ls clients/{client_id}/profile/` to find the most recent \
profile (latest `YYYY-MM-DD` prefix), then `attach_path` to load it.
2. Use `run_command ls clients/{client_id}/treatment-plan/` to find the most \
recent treatment plan, then `attach_path` to load it.
3. Use `run_command ls clients/{client_id}/wellness-assessments/` to list \
previous assessments.
   - If no previous assessments exist: this is an **initial** administration.
   - If previous assessments exist: this is a **re-administration** \
(#N where N = count + 1). Load all previous assessments with `attach_path` \
for trend comparison.

"""
    + WA_SCORING_RULES
    + """
## Map

### Phase 1: Score & Summarize
1. Load client context and determine administration type (see above).
2. Extract all item responses from the input data.
3. Calculate the GD score (sum items 1-15).
4. Determine severity level.
5. If initial administration: calculate CAGE-AID score (items 22-24).
6. **State** the scores in 1-2 sentences (e.g., "GD = 28/45 (Severe); CAGE-AID = 0/3 \
(Negative)"), then **immediately proceed to Phase 2 tool calls in the same response**.

If any item responses are ambiguous or unclear, use the interview tool to ask the clinician about the specific items before proceeding.

### Phase 2: Write File
7. Call `write_file` to create:
   - `wellness-assessments/{date}-wellness-assessment.md`

Save the file under `clients/{client_id}/`.

"""
    + WA_OUTPUT_FORMAT
    + "\n"
)

WA_FILE_MAP_PROMPT = (
    """\
You are processing a Wellness Assessment (Optum Form G22E02) and calculating \
structured scores. Today's date is {date}.

## How to Use This Map

This map contains reference information and workflow steps for scoring a G22E02 \
Wellness Assessment. Loading this map does not mean you must execute the \
workflow. The Phase blocks, "Save ALL files" instructions, and any "immediately \
proceed" directives below are the workflow — they apply only when execution is \
the intent.

- **Execution mode** — Use this when the user clearly asked you to score or \
process a wellness assessment (e.g., "score this WA," "process the G22E02," or \
any slash command that maps to this workflow). Follow the phases below in order, \
including the client-context loading steps and the file write.
- **Reference mode** — Use this when the user is asking a question, comparing \
options, or thinking through a decision related to wellness assessments. Answer \
the user's actual question using the content below as reference. You MAY still \
load specific client files with `attach_path` or `run_command` if you need them \
to answer well (e.g., to look up a prior GD score for trend context). What you \
MUST NOT do in reference mode: auto-execute the canned phase sequence, bulk-load \
every file the workflow normally touches, or call `write_file`/`apply_patch` \
unless the user explicitly confirms they want the documents produced.

When in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Input

The user wants to process a Wellness Assessment from a file. The input is: \
`{file_reference}`

Extract the file path from the input. Use the appropriate tool:
- **PDF files** (.pdf): call `extract_document(path=...)` to extract text. If the \
extracted text only contains form labels without actual response data (e.g., shaded \
circles or handwritten answers are missing), use `attach_path(path=...)` to load the \
PDF visually and read the responses directly.
- **Image files** (.jpg, .png, .heic, etc.): call `attach_path(path=...)` to load
- **Other files**: call `attach_path(path=...)` to load into context

If the path contains shell escape characters (backslashes before spaces, quotes, \
etc.), interpret them as a shell would.

## Client Context

Client ID: `{client_id}`

Load client context and determine administration type:
1. Use `run_command ls clients/{client_id}/profile/` to find the most recent \
profile (latest `YYYY-MM-DD` prefix), then `attach_path` to load it.
2. Use `run_command ls clients/{client_id}/treatment-plan/` to find the most \
recent treatment plan, then `attach_path` to load it.
3. Use `run_command ls clients/{client_id}/wellness-assessments/` to list \
previous assessments.
   - If no previous assessments exist: this is an **initial** administration.
   - If previous assessments exist: this is a **re-administration** \
(#N where N = count + 1). Load all previous assessments with `attach_path` \
for trend comparison.

"""
    + WA_SCORING_RULES
    + """
## Map

### Phase 1: Process File, Score & Summarize
1. Load the WA file using the appropriate tool.
2. Load client context and determine administration type (see above).
3. Extract all item responses from the form.
4. Calculate the GD score (sum items 1-15).
5. Determine severity level.
6. If initial administration: calculate CAGE-AID score (items 22-24).
7. **State** the scores in 1-2 sentences, then **immediately proceed to Phase 2 \
tool calls in the same response**.

If any item responses are ambiguous or unclear from the extracted data, \
use the interview tool to ask the clinician about the specific items before proceeding.

### Phase 2: Write File
8. Call `write_file` to create:
   - `wellness-assessments/{date}-wellness-assessment.md`

Save the file under `clients/{client_id}/`.

"""
    + WA_OUTPUT_FORMAT
    + "\n"
)
