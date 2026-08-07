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
- `estimate_mastery`
- `recommend_review`

## Error memory (`domain-model.md`)

- `search_mistakes`
- `save_mistake`
- `get_recent_mistakes`

## Sessions (`learning-engine.md`)

- `create_session`
- `finish_session`
- `summarize_session`

## Language module (delegates to `Language-Lab` once integrated — see
`roadmap.md`)

- `get_language_profile`
- `get_curriculum`
- `retrieve_vocabulary`

## Stats

- `get_learning_statistics`
