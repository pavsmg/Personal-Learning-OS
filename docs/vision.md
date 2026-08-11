# Vision

A personal voice assistant, usable from computer or phone, for natural
spoken conversation to learn, review, and organize knowledge across the
whole Obsidian vault — informatique (Linux, algorithms, data structures,
AI...), math, physics, languages, sport (strength training, calisthenics...),
and anything else being learned. Not a simple chatbot: a genuine personal
coach that knows the knowledge base, past mistakes, which foundational
concepts are solid per domain, and progression over time. ("Level" here
means demonstrated conceptual understanding, not overall skill — see
`pedagogy.md`'s "Realistic goals" for why conversation can honestly claim
the former but not the latter.)

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

## Career/CV coaching

Because the system tracks per-domain mastery and mistake history over time
(`domain-model.md`), it can also turn that record outward: summarize actual
technical strengths into CV-ready language, and — given a target job
description — say which of those strengths to foreground and which gaps
still need work before applying. This reads the same learner-profile data
every other feature reads; it doesn't require a separate skill-tracking
system.

## Core principle

A single conversation should simultaneously: practice a skill, check
understanding of its foundational concepts, detect new mistakes, update the
learner profile, reinforce important knowledge, and prepare the next session
intelligently. The more
the system gets used, the better it knows the learner, the better it
adapts, and the faster learning compounds — across every domain in the
vault, not just one at a time.

See `roadmap.md` for how this gets built incrementally, and
`architecture.md` for the design principle (backend owns the logic) that
makes each piece of this achievable independently.

## Future Ideas

Not implemented — a backlog of ideas raised in conversation, kept here so
they aren't lost. Nothing below is committed to; revisit and prioritize
deliberately rather than building any of this reactively mid-session.

### Cross-domain innovation engine

Generate new ideas — business ideas, or open research/investigation
directions — by combining knowledge domains the learner has already built
real depth in, rather than working from a fixed, manually-curated field
list. "Depth" here should be grounded in the vault's actual structure — its
MOCs (Machine Learning, Physics, Chemistry, Signal Processing, Languages,
Cybersecurity, Fitness, ...) and eventually the per-domain mastery data
`domain-model.md` already plans to track — so a suggested combination
reflects genuine expertise rather than surface-level vocabulary from a field
barely touched.

Two distinct output modes: **business ideas** (an intersection that
suggests a concrete product, tool, or service — e.g. signal processing +
cybersecurity → acoustic side-channel detection) and **research directions**
(an intersection framed as an open question worth investigating, not
necessarily commercial).

Architecturally, this is the same shape as Career/CV coaching above — it
reads the same learner-profile/mastery data every other feature reads and
turns it outward into something new, rather than needing its own separate
tracking system.

Open questions: whether cluster selection should be automatic (system
proposes pairings, weighted toward mastery) or learner-directed (name two
fields, get the intersection) or both; whether combinations should stay
pairwise or allow three or more fields at once; and what "depth" actually
means before real mastery tracking exists — a simple note-count-per-MOC
proxy in the meantime, maybe.
