# Decisions

Architecture Decision Record log. Every nontrivial choice made on this
project gets an entry here, written when the choice is made — not
reconstructed after the fact. Format: Context / Decision / Status.

Entries 1–7 below are seeded from the original brainstorming conversation
(2026-08-05) that produced this project's vision — they're marked
**Proposed** rather than **Decided** except where the source material
already treated them as settled, since nothing has actually been built
against them yet. Revisit and confirm (or revise) each one as the relevant
part of the roadmap is actually reached, rather than treating them as
locked in from day one.

---

## 1. Backend owns domain logic; the model only handles conversation and tool selection

**Context:** Deciding where retrieval, mastery calculation, session
planning, spaced repetition, memory storage, and scheduling should live —
in the LLM's prompt/reasoning, or in backend code the LLM calls into.

**Decision:** All of that logic lives in the backend as durable,
provider-independent code (`architecture.md`). The model's job is limited
to conversation, reasoning, explanation, tone, and deciding which tool to
call.

**Status:** Proposed.

---

## 2. Provider resilience extends to every component, not just the conversation layer

**Context:** `Language-Lab` already has a "provider independence"
principle, but scoped only to the real-time conversation provider.

**Decision:** Extend the same principle to every component — voice model,
LLM, transcription engine, embedding engine, search engine. Each must be
swappable without touching durable data (knowledge, mistakes, progression).

**Status:** Proposed.

---

## 3. Modular architecture, one module per capability

**Context:** Needed a structure that supports building incrementally and
replacing any one component per decision #2.

**Decision:** Separate modules for knowledge retrieval, error retrieval,
session planning, question generation, real-time conversation, evaluation,
memory, sync, transcription, conversation analysis, plus the existing
Language-Lab module.

**Status:** Proposed.

---

## 4. MCP exposure deferred past the voice MVP

**Context:** MCP would let other AI surfaces (Claude Code, Claude Desktop,
Cursor) query the learning engine directly. But the OpenAI Realtime API's
function calling doesn't go through MCP, so it adds nothing to the voice
loop itself.

**Decision:** Build the voice MVP first; MCP server is a later-stage
addition (`mcp.md`), valuable for secondary non-voice clients, not core to
initial build.

**Status:** Proposed.

---

## 5. OpenAI Realtime API as the initial voice provider

**Context:** Needed a concrete first real-time voice provider to start
building/testing against. `Language-Lab` already uses ElevenLabs for its
own conversational agents.

**Decision:** Start with the OpenAI Realtime API (low latency, WebRTC,
interruptions, function calling) — deliberately a different choice from
Language-Lab's ElevenLabs, and explicitly a starting point for
experimentation, not a permanent commitment (see decision #2).

**Status:** Proposed.

---

## 6. Text-first build order

**Context:** Realtime audio adds meaningful complexity (latency,
interruption handling, transcription) on top of the core learning-engine
logic.

**Decision:** Validate the learning engine and tool-calling loop over
text-only conversations first (`roadmap.md`, steps 1–6) before adding
voice (steps 7–8).

**Status:** Proposed.

---

## 7. Language-Lab stays separate until Personal Learning OS reaches build stage

**Context:** `Language-Lab` (`~/Language-Lab`) already implements a
scoped-down version of this vision for language practice specifically, with
its own independently-evolving backlog.

**Decision:** The two stay separate projects for now. `Language-Lab`
continues evolving independently. Once Personal Learning OS moves from idea
to build, `Language-Lab` gets integrated as its language-learning module
rather than rebuilt from scratch — its CEFR/curriculum/vocabulary handling
becomes one domain plugged into the bigger system.

**Status:** Decided (2026-08-05) — this one was already settled in the
original vision note, unlike 1–6 above.
