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

## Evidence (decisions.md #44)

The two-sided counterpart to a mistake entry: a mistake row is written
when something goes wrong, an evidence row is written for the graded
outcome of every planned concept at the end of a session — success
included, not just failure. Written once per session by an LLM-judged
pass over that session's transcript (`sessions/grading.py`), not per
turn — the same tool-calling burden rule 3 already fights for isn't
doubled by also asking for a per-turn "success" call.

Fields:

- domain
- concept
- timestamp
- outcome — one of `not_reached` / `incorrect` / `partial` / `correct` /
  `correct_with_application` (the last requires a rule-11 novel-scenario
  transfer question actually cleared, not just a correct definition)
- quality — how strongly the transcript evidence supports this specific
  grade (0–1), distinct from `outcome`'s discrete performance level
- source — which pass produced this row (`"session_grading"` today)
- session_id

`not_reached` is a real, written outcome for a planned concept the
session never actually quizzed — recorded so it isn't silently dropped,
but never scored: mere discussion isn't evidence of understanding, only
an actual recall/production check is (`pedagogy.md`'s illusion-of-
competence concern, extended to this table). Existing `mistakes` rows are
read alongside `evidence` rows as negative evidence, not migrated into
this table — both stay the source of truth for conceptual understanding
together.

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

The currently-implemented `MasteryEstimate` (`mistakes/models.py`) is
`conceptual_understanding: float`, `mistake_count: int` (mistakes-table
rows only, its original meaning), and `observation_count: int` (the
two-sided total across both tables, decisions.md #44) per (domain,
concept). It still doesn't distinguish conceptual from applied
competence within that single scalar — `correct_with_application`
evidence moves the score by contributing a stronger observation, not by
tracking applied competence as a separate field — a real, still-open gap
this schema hasn't closed.

## Session

See `learning-engine.md` for the full session lifecycle. At the domain
model level, a session is the unit that ties everything together: it
consumes learner-profile and mistake data going in, and produces updates to
both plus a summary going out.
