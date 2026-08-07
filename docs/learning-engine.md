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

The conversation itself then follows:

```
start → planner builds the session → relevant memories retrieved →
assistant opens naturally → questions adapt dynamically → session ends →
summary generated → memory updated → next review scheduled
```

Planning and wrap-up are backend responsibilities; only the middle — the
actual talking — belongs to the model (see `architecture.md`'s "backend
owns the logic" principle).

## Core principle

A single conversation should simultaneously: practice a skill, evaluate
current level, detect new mistakes, update the learner profile, reinforce
important knowledge, and prepare the next session intelligently. See
`vision.md` for the full statement of this principle and why it's the
project's north star.
