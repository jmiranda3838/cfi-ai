"""Clinical prompt templates for the /session map (ongoing progress notes)."""

from cfi_ai.prompts.narrative_therapy import NARRATIVE_THERAPY_PRINCIPLES
from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS

SESSION_MAP_PROMPT = (
    """\
You are generating an Optum-compliant progress note for an ongoing therapy session. \
Today's date is {date}.

## How to Use This Map

This map contains reference information and workflow steps for ongoing-session \
progress notes. Loading this map does not mean you must execute the workflow. The \
Phase blocks, "Save ALL files" instructions, and any "immediately proceed" \
directives below are the workflow — they apply only when execution is the intent.

- **Execution mode** — Use this when the user clearly asked you to produce or \
update a session progress note (e.g., "write the session note," "do a progress \
note for today's session," or any slash command that maps to this workflow). \
Follow the phases below in order, including the client-context loading steps and \
the file writes.
- **Reference mode** — Use this when the user is asking a question, comparing \
options, or thinking through a decision related to session notes. Answer the \
user's actual question using the content below as reference. You MAY still load \
specific client files with `attach_path` or `run_command` if you need them to \
answer well (e.g., to look up the current treatment plan or a recent note). \
What you MUST NOT do in reference mode: auto-execute the canned phase sequence, \
bulk-load every file the workflow normally touches, or call \
`write_file`/`apply_patch` unless the user explicitly confirms they want the \
documents produced.

When in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Resolving Client Context

If the user hasn't named a client, ask via `interview`. If the name is \
ambiguous or misspelled, run `run_command ls clients/` to see which client \
directories exist, and use `interview` to disambiguate when needed.

Once you have a confirmed client-id slug, load the client's most recent profile \
and treatment plan:

1. `run_command ls clients/<client-id>/profile/` — find the latest \
`YYYY-MM-DD` prefix, then `attach_path` to load it.
2. `run_command ls clients/<client-id>/treatment-plan/` — find the latest \
treatment plan, then `attach_path` to load it.

## Processing Session Input

The user may provide session input in several forms. Pick the appropriate path:

- **File paths** (audio `.m4a`/`.mp3`/`.wav`, PDFs, images): process each file with \
the right tool:
  - Audio → `attach_path(path=...)` to load into context, then transcribe directly.
  - PDF → `extract_document(path=...)` for text. If the extracted text is \
incomplete or only contains form labels, fall back to `attach_path(path=...)` \
to read the PDF visually.
  - Other files → `attach_path(path=...)`.
  If a path contains shell escape characters (backslashes before spaces, quotes), \
interpret them as a shell would — e.g. `Bristol\\ St\\ 4.m4a` means \
`Bristol St 4.m4a`.
- **Pasted transcript text**: use it directly as the session transcript.
- **Neither provided**: call `interview` to ask what form the session content \
is in and where to find it. Do not proceed to Phase 2 without a transcript or \
audio.

When transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content.

## Map

### Phase 1: Load Context & Summarize
1. Resolve the client and load profile + treatment plan (see above).
2. Process the session input to produce session content (see above).
3. **Check the loaded profile for a "Billing & Provider Information" section.** \
If it is missing or incomplete (no Payer, no Default Modality, no Supervised \
flag, etc.), call `interview` ONCE to collect: payer, authorization number \
(if EAP/EWS), total authorized sessions, authorization period, default \
modality (In-Person/Video/Phone), supervised (Y/N), supervisor name + license \
+ NPI if supervised, supervision format, service setting/POS. The new note \
CANNOT be generated without this data — billing fields #4–#8 depend on it. \
After collecting the answers, plan to `write_file` (overwrite=true) the \
updated profile in the same Phase 2 batch as the progress note. This is a \
ONE-TIME backfill — subsequent sessions will read the section directly.
4. Review the session content and client context.
5. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
6. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `clients/<client-id>/sessions/{date}-progress-note.md`
   - `clients/<client-id>/sessions/{date}-session-transcript.md`
   - `clients/<client-id>/profile/{date}-profile.md` (ONLY if you backfilled \
the Billing & Provider section in Phase 1 step 3 — use overwrite=true and \
include the full existing profile content with the new billing section \
appended)

Emit all `write_file` calls together. The user will review and approve. \
For audio sources, the session transcript should include speaker labels \
(e.g. "Therapist:", "Client:") — capture dialogue faithfully including filler \
words, pauses noted in brackets, and emotional tone observations in brackets \
where clinically relevant. If the source was an audio file, the transcript \
file should note that it was transcribed from audio in its header.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  sessions/<YYYY-MM-DD>-progress-note.md      (TheraNest 30-field progress note)
  sessions/<YYYY-MM-DD>-session-transcript.md (verbatim or transcribed session)
```

{progress_note_guidance}
"""
)
