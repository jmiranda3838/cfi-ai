"""Clinical prompt templates for the /session map (ongoing progress notes)."""

from cfi_ai.prompts.narrative_therapy import NARRATIVE_THERAPY_ORIENTATION

SESSION_MAP_PROMPT = (
    """\
You are generating a progress note for an ongoing therapy session. Today's date is {date}.

## Resolving Client Context

If the user hasn't named a client, ask via `interview`. If the name is \
ambiguous, disambiguate against `clients/`. Then load the client's most \
recent profile and treatment plan from `clients/<client-id>/profile/` and \
`clients/<client-id>/treatment-plan/`.

## Processing Session Input

Session input arrives as audio, a transcript file, or pasted transcript text. \
Load files into context with the appropriate tool (see system prompt). When \
transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content. If no session input is provided, call `interview` to ask \
what form the content is in and where to find it. Do not proceed to Phase 2 \
without a transcript or audio.

## Map

### Phase 1: Resolve Payer & Context, Process Input, Summarize
1. Resolve the client and load the most recent profile + treatment plan (see above).
2. **Resolve the payer + billing context from the profile.** The profile's \
"Billing & Provider Information" section carries the Payer field plus billing \
data the progress note depends on (modality, supervision, POS, etc.).
   - If the section is present with a Payer, map the payer name to a slug:
     - `"Optum EWS/EAP"` or `"Optum EAP"` → `optum-eap`
     - `"Aetna"` → `aetna`
     - `"Evernorth"` → `evernorth`
   - If the section is missing or incomplete (no Payer, no Default Modality, \
no Supervised flag, etc.), call `interview` ONCE to collect: payer, \
authorization number, total authorized sessions, authorization period, default \
modality (In-Person/Video/Phone), supervised (Y/N), supervisor name + license \
+ NPI if supervised, supervision format, service setting/POS. The new note \
CANNOT be generated without this data. After collecting the answers, plan to \
`write_file` (overwrite=true) the updated profile in the same Phase 2 batch \
as the progress note. This is a ONE-TIME backfill — subsequent sessions will \
read the section directly.

   Once you have a payer slug, call `load_payer_rules(payer=<slug>)` exactly \
once. The returned rules govern CPT-code selection, modifier flags, \
authorization handling, and any required assessments for the rest of this \
workflow. If the payer's rules don't require authorization, leave \
authorization fields blank.
3. Process the session input to produce session content (see above).
4. Review the session content and client context.
5. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
6. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `clients/<client-id>/sessions/{date}-progress-note.md`
   - `clients/<client-id>/sessions/{date}-session-transcript.md`
   - `clients/<client-id>/profile/{date}-profile.md` (ONLY if you backfilled \
the Billing & Provider section in Phase 1 step 2 — use overwrite=true and \
include the full existing profile content with the new billing section \
appended)

For audio sources, the session transcript should include speaker labels \
(e.g. "Therapist:", "Client:") — capture dialogue faithfully including filler \
words, pauses noted in brackets, and emotional tone observations in brackets \
where clinically relevant. If the source was an audio file, the transcript \
file should note that it was transcribed from audio in its header.

"""
    + NARRATIVE_THERAPY_ORIENTATION
    + "\n"
    + "{progress_note_guidance}\n"
)
