"""Clinical prompt templates for the /wellness-assessment map (G22E02).

Also the single source of truth for the WA scoring rules and output format —
moved from `prompts/shared.py` since they're used exclusively by this map.
"""

from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS

WA_SCORING_RULES = """\
## Scoring Rules

### Global Distress (GD) Scale — Items 1-15
- Sum all 15 items. Range: 0-45.
- **Items 1-11** (symptom burden): Not at All=0, A Little=1, Somewhat=2, A Lot=3
- **Items 12-15** (wellbeing — already reverse-aligned on the form):
  Strongly Agree=0, Agree=1, Disagree=2, Strongly Disagree=3
- All items are scored so that higher = more distress. No manual reversal needed.

### Severity Thresholds
| Range | Severity | Clinical Significance |
|-------|----------|----------------------|
| 0-11 | Low | Below clinical cutoff |
| 12-24 | Moderate | At or above cutoff |
| 25-38 | Severe | Significant distress |
| 39-45 | Very Severe | Acute distress |

Clinical cutoff: **12** (GD >= 12 indicates clinically significant distress).

### CAGE-AID Screen (Items 22-24) — Initial Administration Only
- Count "Yes" responses. Range: 0-3.
- Any "Yes" = positive screen (flag substance use risk).

### Item 16 — Alcohol Use
- Number of drinks in past week. Document but do not formally score.

### Items 17-24 — Initial Administration Only
- Items 17-21: Health and workplace functioning. Document in table.
- Items 22-24: CAGE-AID (scored above).
- Re-administrations use items 1-16 only.

### Missing Data
- Up to 3 missing items on GD scale: impute score of 1 for each missing item.
- More than 3 missing items: mark GD score as **Invalid** and note which items \
are missing.
- If the form is partially completed, note which items are missing.
"""

WA_OUTPUT_FORMAT = """\
Use this format:

```
# Wellness Assessment (G22E02)

- **Client ID:** [client-id slug]
- **Date:** {date}
- **Administration:** [Initial | Re-administration (#N)]
- **Visit #:** [number]

## Global Distress (GD) Scale — Items 1-15

| # | Item | Response | Score |
|---|------|----------|-------|
| 1 | Nervousness or shakiness | [text] | [0-3] |
| 2 | Feeling no interest in things | [text] | [0-3] |
| 3 | Feeling hopeless about the future | [text] | [0-3] |
| 4 | Feeling blue | [text] | [0-3] |
| 5 | Worrying too much about things | [text] | [0-3] |
| 6 | Trouble falling asleep or staying asleep | [text] | [0-3] |
| 7 | Feeling everything is an effort | [text] | [0-3] |
| 8 | Feeling tense or keyed up | [text] | [0-3] |
| 9 | Having spells of terror or panic | [text] | [0-3] |
| 10 | Feeling restless or can't sit still | [text] | [0-3] |
| 11 | Feeling worthless | [text] | [0-3] |
| 12 | I have good self-esteem | [text] | [0-3] |
| 13 | I am able to cope with whatever comes my way | [text] | [0-3] |
| 14 | I am able to accomplish the things I set out to do | [text] | [0-3] |
| 15 | Friends/family I can count on | [text] | [0-3] |

- **GD Score:** [sum]/45
- **Severity:** [Low/Moderate/Severe/Very Severe]

## Alcohol Use (Q16)
- Drinks in past week: [number]

## CAGE-AID Screen (Q22-24) — Initial Only

| # | Question | Response |
|---|----------|----------|
| 22 | ... | Yes/No |
| 23 | ... | Yes/No |
| 24 | ... | Yes/No |

- **CAGE-AID Score:** [0-3]
- **Screen Result:** [Negative/Positive]

## Health & Workplace Items (Q17-21) — Initial Only

| # | Item | Response |
|---|------|----------|
| 17 | ... | ... |
| 18 | ... | ... |
| 19 | ... | ... |
| 20 | ... | ... |
| 21 | ... | ... |

## Score Trend (re-administrations only)

| Date | GD Score | Severity | Change |
|------|----------|----------|--------|
| [prior date] | [score] | [level] | -- |
| {date} | [score] | [level] | [+/-N] |

## Clinical Summary
[1-2 sentences: for initial, baseline context and clinical significance; \
for re-administrations, trend interpretation and treatment implications]

## Progress Note Snippet
[Ready-to-paste text for the Data section of the next progress note, e.g.: \
"Wellness Assessment (G22E02) administered: Global Distress = 28/45 (Severe); \
CAGE-AID = 0/3 (Negative)."]
```

For re-administrations, omit the CAGE-AID and Health & Workplace sections. \
Include the Score Trend table with all prior scores plus the current one.

For initial administrations, omit the Score Trend section.
"""

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
## Resolving Client Context

If the user hasn't named a client, ask via `interview`. If the name is \
ambiguous or misspelled, run `run_command ls clients/` to see which client \
directories exist, and use `interview` to disambiguate.

Once you have a confirmed client-id slug, load context and determine \
administration type:

1. `run_command ls clients/<client-id>/profile/` — find the most recent \
profile (latest `YYYY-MM-DD` prefix), then `attach_path` to load it.
2. `run_command ls clients/<client-id>/treatment-plan/` — find the most \
recent treatment plan, then `attach_path` to load it.
3. `run_command ls clients/<client-id>/wellness-assessments/` — list \
previous assessments.
   - If no previous assessments exist: this is an **initial** administration.
   - If previous assessments exist: this is a **re-administration** \
(#N where N = count + 1). Load all previous assessments with `attach_path` \
for trend comparison.

## Processing WA Input

The user may provide the assessment in several forms:

- **PDF file** (.pdf): `extract_document(path=...)` to extract text. If the \
extracted text only contains form labels without actual response data (shaded \
circles, handwritten answers), fall back to `attach_path(path=...)` to load \
the PDF visually and read the responses directly.
- **Image file** (.jpg, .png, .heic, etc.): `attach_path(path=...)` to load.
- **Other files**: `attach_path(path=...)`.
- **Pasted responses** in the conversation: use them directly.
- **Nothing provided**: call `interview` to ask where the WA data is (file \
path, paste, paper scan).

If a path contains shell escape characters (backslashes before spaces, quotes), \
interpret them as a shell would.

If any item responses are ambiguous or unclear from the extracted data, use \
`interview` to ask the clinician about the specific items before scoring.

"""
    + WA_SCORING_RULES
    + """
## Map

### Phase 1: Score & Summarize
1. Resolve the client and load context (see above).
2. Process the WA input into item-level responses (see above).
3. Calculate the GD score (sum items 1-15).
4. Determine severity level.
5. If initial administration: calculate CAGE-AID score (items 22-24).
6. **State** the scores in 1-2 sentences (e.g., "GD = 28/45 (Severe); CAGE-AID \
= 0/3 (Negative)"), then **immediately proceed to Phase 2 tool calls in the \
same response**.

### Phase 2: Write File
7. Call `write_file` to create:
   - `clients/<client-id>/wellness-assessments/{date}-wellness-assessment.md`

"""
    + WA_OUTPUT_FORMAT
    + "\n"
)
