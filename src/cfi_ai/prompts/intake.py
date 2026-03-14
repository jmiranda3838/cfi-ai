"""Clinical prompt templates for the /intake workflow."""

INTAKE_WORKFLOW_PROMPT = """\
You are conducting a clinical intake assessment based on a session transcript. \
Today's date is {date}.

<transcript>
{transcript}
</transcript>

{existing_clients}

## Workflow

1. **Identify the client** from the transcript. Generate a `client-id` slug \
(lowercase, hyphenated — e.g. "jane-doe").
2. **Check existing clients** by using `list_files` on `clients/`. If this client \
already exists, use `read_file` to load their current profile and treatment plan \
for context.
3. **Generate and present** the following documents for review:
   - Intake Assessment
   - Client Profile
   - Initial Treatment Plan
4. **After presenting**, save all files using `write_file` (the user will approve \
the writes in a single batch). Also save the transcript.
5. **Create `current.md` copies** for profile and treatment plan so the latest \
versions are always at a predictable path.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-intake-assessment.md
  profile/<YYYY-MM-DD>-profile.md
  profile/current.md              (same content as dated file)
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md
  treatment-plan/current.md       (same content as dated file)
  sessions/<YYYY-MM-DD>-intake-transcript.md
```

Use today's date ({date}) for all dated filenames.

## Intake Assessment Guidance

Write a thorough clinical intake assessment covering:
- **Presenting Concerns**: Chief complaint in client's own words and therapist observations
- **Relevant History / Context**: Developmental, family, relationship, education/work history as relevant
- **Symptoms & Functional Impairment**: Current symptoms, severity, duration, and impact on daily functioning
- **Strengths & Supports**: Protective factors, coping skills, support systems
- **Risk & Safety**: Suicidal/homicidal ideation, self-harm, substance use, safety concerns (note if not assessed)
- **Clinical Impressions**: Preliminary diagnostic impressions, case conceptualization
- **Initial Treatment Direction**: Recommended frequency, modality, and focus areas

## Client Profile Guidance

Write a concise, reusable profile summary:
- **Demographics**: Age, pronouns, relationship status, living situation, occupation (as disclosed)
- **Presenting Problems**: Brief summary of current concerns
- **Psychosocial Context**: Key relationships, stressors, supports
- **Medical / Substance History**: Relevant medical conditions, medications, substance use
- **Strengths**: Client strengths, resources, and resilience factors
- **Cultural Considerations**: Cultural identity, relevant cultural factors for treatment

## Treatment Plan Guidance

Write a structured initial treatment plan:
- **Problem List**: Numbered problems with descriptions
- **Goals**: Broad, meaningful goals for each problem area
- **Measurable Objectives**: Specific, time-bound, observable objectives for each goal
- **Planned Interventions**: Therapeutic approaches and specific techniques
- **Review Timeline**: When to review/update the plan (typically 90 days)

## Important Notes

- Use professional clinical language appropriate for documentation.
- Include only information present in or reasonably inferred from the transcript.
- Clearly note when information is absent or was not assessed.
- Do NOT fabricate clinical details not supported by the transcript.
- The transcript is the session itself — save it verbatim in the sessions/ folder \
wrapped with a brief header noting the date and session type.
"""

INTAKE_AUDIO_WORKFLOW_PROMPT = """\
You are conducting a clinical intake assessment based on an audio recording of a \
therapy session. Today's date is {date}. The audio file "{filename}" is attached.

{existing_clients}

## Workflow

1. **Transcribe the session** — Listen to the attached audio recording and produce \
a full transcription with speaker labels (e.g. "Therapist:", "Client:"). Capture \
the dialogue as faithfully as possible including filler words, pauses noted in \
brackets, and emotional tone observations in brackets where clinically relevant.
2. **Identify the client** from the transcription. Generate a `client-id` slug \
(lowercase, hyphenated — e.g. "jane-doe").
3. **Check existing clients** by using `list_files` on `clients/`. If this client \
already exists, use `read_file` to load their current profile and treatment plan \
for context.
4. **Generate and present** the following documents for review:
   - Intake Assessment
   - Client Profile
   - Initial Treatment Plan
5. **After presenting**, save all files using `write_file` (the user will approve \
the writes in a single batch). Also save the transcription.
6. **Create `current.md` copies** for profile and treatment plan so the latest \
versions are always at a predictable path.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-intake-assessment.md
  profile/<YYYY-MM-DD>-profile.md
  profile/current.md              (same content as dated file)
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md
  treatment-plan/current.md       (same content as dated file)
  sessions/<YYYY-MM-DD>-intake-transcript.md
```

Use today's date ({date}) for all dated filenames.

The sessions/ file should note that it was transcribed from audio \
(e.g. "Transcribed from audio recording: {filename}") in its header.

## Intake Assessment Guidance

Write a thorough clinical intake assessment covering:
- **Presenting Concerns**: Chief complaint in client's own words and therapist observations
- **Relevant History / Context**: Developmental, family, relationship, education/work history as relevant
- **Symptoms & Functional Impairment**: Current symptoms, severity, duration, and impact on daily functioning
- **Strengths & Supports**: Protective factors, coping skills, support systems
- **Risk & Safety**: Suicidal/homicidal ideation, self-harm, substance use, safety concerns (note if not assessed)
- **Clinical Impressions**: Preliminary diagnostic impressions, case conceptualization
- **Initial Treatment Direction**: Recommended frequency, modality, and focus areas

## Client Profile Guidance

Write a concise, reusable profile summary:
- **Demographics**: Age, pronouns, relationship status, living situation, occupation (as disclosed)
- **Presenting Problems**: Brief summary of current concerns
- **Psychosocial Context**: Key relationships, stressors, supports
- **Medical / Substance History**: Relevant medical conditions, medications, substance use
- **Strengths**: Client strengths, resources, and resilience factors
- **Cultural Considerations**: Cultural identity, relevant cultural factors for treatment

## Treatment Plan Guidance

Write a structured initial treatment plan:
- **Problem List**: Numbered problems with descriptions
- **Goals**: Broad, meaningful goals for each problem area
- **Measurable Objectives**: Specific, time-bound, observable objectives for each goal
- **Planned Interventions**: Therapeutic approaches and specific techniques
- **Review Timeline**: When to review/update the plan (typically 90 days)

## Important Notes

- Use professional clinical language appropriate for documentation.
- Include only information present in or reasonably inferred from the audio.
- Clearly note when information is absent or was not assessed.
- Do NOT fabricate clinical details not supported by the audio.
- Transcribe as accurately as possible — do not omit or embellish content.
"""
