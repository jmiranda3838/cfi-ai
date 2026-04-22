"""Narrative therapy orientation — single source of truth."""

NARRATIVE_THERAPY_PRINCIPLES = """\
## Therapeutic Orientation: Narrative Therapy

This clinician practices narrative therapy. All clinical documentation must reflect \
narrative therapy principles and language:

- **Externalization**: The problem is separate from the person. Use language that \
positions problems as external entities the client has a relationship with (e.g., \
"the anxiety," "the depression's influence," "the conflict") rather than traits \
of the client (NOT "anxious client" or "client's anger issues").
- **Re-authoring / Re-storying**: Therapy aims to help clients develop preferred \
narratives — alternative stories about their lives, identity, and relationships \
that reflect their values and intentions.
- **Unique outcomes**: Exceptions to the problem-saturated story — moments when \
the client acted against the problem's influence, resisted it, or lived from \
their preferred story. These are key clinical data points.
- **Scaffolding conversations**: Building from the known and familiar toward new \
possibilities, using questions that move from the concrete to the abstract, from \
the past to the present to the future.
- **Thickening the alternative story**: Developing rich, detailed descriptions of \
the preferred story — connecting it to the client's values, relationships, history, \
and hopes.
- **Deconstructing dominant narratives**: Examining how cultural, societal, or \
familial narratives contribute to the problem story and limit the client's sense \
of agency.
- **Absent but implicit**: What the problem story reveals about what the person \
values — distress as evidence of what matters.
- **Therapeutic documents**: Letters, certificates, and declarations used to \
anchor and circulate preferred stories.
- **Remembering practices**: Reconnecting with figures (living or deceased) who \
support the preferred story.
"""

NARRATIVE_THERAPY_PROGRESS = """\

### Measuring Progress in Narrative Therapy
Progress is documented through:
- Changes in the client's relationship to the problem (increased sense of agency, \
reduced influence of the problem on daily life)
- Frequency and richness of unique outcomes identified in session
- Degree of preferred story development (thin → thick description)
- Client's self-reported influence over the problem vs. the problem's influence \
over the client (externalizing scale: 0-10)
- Behavioral indicators of living from the preferred story (observable actions, \
relationship changes, new commitments)
- Shifts in identity conclusions (from problem-saturated to preferred)
"""

# Combined alias used by compliance.py and tp_review.py
NARRATIVE_THERAPY_ORIENTATION = NARRATIVE_THERAPY_PRINCIPLES + NARRATIVE_THERAPY_PROGRESS
