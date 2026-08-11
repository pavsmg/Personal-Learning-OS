# Domain Model

The core entities the backend tracks, independent of any specific
provider or UI. These are what `tools.md`'s functions read and write, and
what `architecture.md`'s provider-resilience principle is protecting.

## Mistake entry

Not just knowledge coverage — a detailed history of actual mistakes:
forgotten concepts, bad explanations, recurring confusions, vocabulary
errors, grammar errors, bad habits, wrong assumptions, whatever's relevant
to the domain. Before a new session, the assistant consults this memory to
decide what needs review, what needs consolidating, and what can be
treated as solid — the same role `MISTAKES.md` plays for one language in
`Language-Lab`, generalized across every tracked domain.

Fields:

- concept
- explanation
- category
- severity
- timestamp
- corrected (bool)
- confidence
- links to related notes (vault wikilinks)

Enough structure that a future session can query it precisely rather than
skim a free-text log.

## Learner profile / mastery

On a request like "quiz me on algorithms," the assistant retrieves the
relevant atomic notes (see `retrieval.md`), understands the relationships
between them, builds a natural conversation from that material, asks
questions, asks for explanations in the learner's own words, detects gaps
as they show up, and adapts the rest of the conversation accordingly —
rather than following a fixed script.

This generalizes what a language-specific `ROADMAP.md` note already does
for one domain (grammar/vocab topics with status) to every domain in the
vault, including ones with no existing roadmap structure at all (math,
physics, sport). A learner profile is the per-domain, per-concept mastery
estimate this retrieval-and-tutoring loop reads and updates.

What "mastery" honestly measures here is conceptual understanding, not
overall competence: whether the learner can produce a concept's definition,
mechanism, or distinction from a related idea on demand — not whether they
can apply it under real, unscripted conditions (solve a novel problem,
execute a skill, use a language spontaneously). See `pedagogy.md`'s
"Realistic goals" for why conversational testing can support the former
reliably but not the latter.

The currently-implemented `MasteryEstimate` (`tools_interface/models.py`) is
a single `mastery: float` per (domain, concept) — it doesn't yet distinguish
conceptual from applied competence, and should be revisited before
`estimate_mastery` (Milestone 6) is actually implemented against it, rather
than building real planner logic around a schema that already overclaims
what it measures.

## Session

See `learning-engine.md` for the full session lifecycle. At the domain
model level, a session is the unit that ties everything together: it
consumes learner-profile and mistake data going in, and produces updates to
both plus a summary going out.
