# Vision

A personal voice assistant, usable from computer or phone, for natural
spoken conversation to learn, review, and organize knowledge across the
whole Obsidian vault — informatique (Linux, algorithms, data structures,
AI...), math, physics, languages, sport (strength training, calisthenics...),
and anything else being learned. Not a simple chatbot: a genuine personal
coach that knows the knowledge base, past mistakes, current level per
domain, and progression over time.

## What it should feel like to use

**Minimal interface.** Nearly invisible — no menus to navigate. The ideal
flow: open the app, talk, listen to the response, end the session. All
logic stays in the backend (see `architecture.md`), not surfaced as UI
complexity.

**Portable across devices.** Works on computer, phone, and eventually
tablet — start a session on a computer, continue it later on a commute with
headphones, so otherwise-dead transit time becomes learning time.

**Synced across devices.** Everything stays current regardless of device:
error memory, conversations, summaries, progression, newly-acquired
knowledge, learning statistics. The experience should be transparent — no
manual export/import step between devices.

## Core principle

A single conversation should simultaneously: practice a skill, evaluate
current level, detect new mistakes, update the learner profile, reinforce
important knowledge, and prepare the next session intelligently. The more
the system gets used, the better it knows the learner, the better it
adapts, and the faster learning compounds — across every domain in the
vault, not just one at a time.

See `roadmap.md` for how this gets built incrementally, and
`architecture.md` for the design principle (backend owns the logic) that
makes each piece of this achievable independently.
