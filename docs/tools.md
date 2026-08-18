# Tool / Function Interface

The realtime model talks to the backend through small, single-purpose
functions rather than a few large ones. Each function does exactly one
thing — avoid "god functions" that bundle multiple responsibilities, since
that's exactly what would make swapping providers (`architecture.md`) hard
later.

## Knowledge (`retrieval.md`)

- `search_notes`
- `get_note`
- `related_notes`

## Progression (`domain-model.md`)

- `get_learning_profile`
- `estimate_mastery` — conceptual understanding of one concept, derived from
  both recorded mistakes and end-of-session graded evidence
  (`decisions.md` #44). Returns `null` for a concept with no recorded
  history: "no evidence yet," which is not the same as understood, and is
  deliberately not reported as a score (`decisions.md` #45).
- `recommend_review`

## Error memory (`domain-model.md`)

- `search_mistakes`
- `save_mistake` — records a live, in-conversation correction (rule 2/3).
  Not the evidence-capture mechanism for successes: those are graded once
  at session end (`decisions.md` #44), not via a per-turn tool, so the
  model is never asked to call a "success" counterpart to this.
- `get_recent_mistakes`

## Sessions (`learning-engine.md`)

- `create_session`
- `finish_session` — also runs the end-of-session evidence-grading pass
  (`decisions.md` #44), backend-orchestrated, not something the model
  triggers or is aware of.
- `summarize_session`

## Language module (delegates to `Language-Lab` once integrated — see
`roadmap.md`)

- `get_language_profile`
- `get_curriculum`
- `retrieve_vocabulary`

## Stats

- `get_learning_statistics`

## Career (`domain-model.md`'s learner profile, read-only)

- `summarize_skills_for_cv` — turn current per-domain mastery into CV-ready
  skill language.
- `analyze_job_fit` — given a target job description, compare it against the
  learner profile: which tracked strengths to foreground, which required
  skills are gaps not yet covered by the profile.
