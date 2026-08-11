# Learning Engine

## Teacher-style conversational agent, general-purpose

Instead of only answering questions, the agent plays teacher: asking
questions, requesting explanations, posing small challenges, interrupting
when an idea is wrong instead of waiting to summarize it afterward, and
coming back later to a concept that was shaky — favoring active recall over
passive reading of notes.

(A scoped-down version of this — "Active-recall / quiz mode for the agent"
— is already in `Language-Lab`'s own backlog for the language-practice case
specifically; this is the general form of the same idea, applicable to any
domain.)

## Session planning & conversation flow

A session shouldn't start cold. Before the conversation begins, a planner
decides the day's objective, which concepts to review, which mistakes are
worth revisiting, target difficulty, and expected duration — drawing on
`retrieval.md` and the mistake-memory data in `domain-model.md`.

The planner builds a session one of two ways:

- **Automatic.** No topic given: the planner picks one itself, driven by
  what's actually due for review (`recommend_review` over mistake-memory,
  once Milestone 6 wires it in) rather than guessing at random — open the
  app with no stated goal, and it proposes what to work on.
- **Learner-directed.** The learner names a topic; the planner builds the
  session around that instead of picking on its own.

Both produce the same `SessionPlan` (`sessions/models.py`) and enter the
same conversation flow below — the difference is only in how the
objective/concepts get chosen. Which mode applies for a given session is a
backend/orchestration decision made *before* the conversation starts
(`create_session` is backend-orchestrated, not model-callable — see
`tools.md`, `decisions.md` #14), not something the model chooses
mid-conversation. Until Milestone 6 lands, only the learner-directed path is
actually implemented — `create_session` currently requires `topic`; see
`milestones.md` Milestone 6.

The conversation itself then follows:

```
start → planner builds the session (automatic or learner-directed) →
relevant memories retrieved → assistant opens naturally → questions adapt
dynamically → session ends → summary generated → memory updated → next
review scheduled
```

Planning and wrap-up are backend responsibilities; only the middle — the
actual talking — belongs to the model (see `architecture.md`'s "backend
owns the logic" principle).

## Core principle

A single conversation should simultaneously: practice a skill, check
understanding of its foundational concepts, detect new mistakes, update the
learner profile, reinforce important knowledge, and prepare the next
session intelligently. See `vision.md` for the full statement of this
principle and why it's the project's north star.
