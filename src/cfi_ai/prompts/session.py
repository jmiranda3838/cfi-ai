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
**immediately proceed to the Phase 2 template-load tool call in the same \
response** — do NOT stop after the summary text.

### Reference-Only Questions
If the user is asking about progress-note structure, required fields, or field \
definitions rather than asking you to generate documents, call \
`load_form_template(template='progress-note')` before answering. Use the \
returned spec as the authoritative reference, and do NOT call `write_file` \
unless the user asks you to create or update files.

### Phase 2: Write Documents
6. Call `load_form_template(template='progress-note')` first. Do NOT call \
`write_file` for the progress note in this response. Wait for the tool result \
to return so you can use the authoritative TheraNest 30-field progress-note \
spec verbatim.
7. After the `load_form_template` result is returned, **in your next response** \
call `write_file` once for EACH required file below. Use the returned progress-note \
spec to structure the progress-note write:
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
)
