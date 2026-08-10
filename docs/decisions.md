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
text-only conversations first (`roadmap.md`, steps 1–7) before adding
voice (steps 8–9).

**Status:** Proposed.

---

## 7. Language-Lab stays separate until Personal Learning OS reaches build stage

**Context:** `Language-Lab` (`~/Projects/Language-Lab`) already implements a
scoped-down version of this vision for language practice specifically, with
its own independently-evolving backlog.

**Decision:** The two stay separate projects for now. `Language-Lab`
continues evolving independently. Once Personal Learning OS moves from idea
to build, `Language-Lab` gets integrated as its language-learning module
rather than rebuilt from scratch — its CEFR/curriculum/vocabulary handling
becomes one domain plugged into the bigger system.

**Status:** Decided (2026-08-05) — this one was already settled in the
original vision note, unlike 1–6 above.

---

## 8. Career/CV coaching added as a scoped feature, placed after mistake-memory (step 7)

**Context:** User requested a feature to summarize tracked technical
strengths into CV-ready language and, given a target job description,
identify which strengths to foreground and which required skills are gaps.
This reads mastery/mistake data that only becomes meaningful once
`domain-model.md`'s learner profile is actually populated by real sessions
— it has nothing to contribute before that.

**Decision:** Add two read-only functions to `tools.md`'s new Career group
(`summarize_skills_for_cv`, `analyze_job_fit`), reusing the existing
learner-profile schema with no new domain-model entities. Placed as
`roadmap.md` step 7 / `milestones.md` Milestone 7 — after Milestone 6
(mistake-memory) so real data exists, before the Realtime/voice work (now
steps 8–9) since it's a text-only capability and the project's text-first
principle (decision #6) says non-voice work belongs before realtime
complexity.

**Status:** Decided (2026-08-10).

---

## 9. Backend language/framework: Python + FastAPI

**Context:** Milestone 0 needs a concrete language/framework to scaffold
against. Neither `Language-Lab` component commits this project to a choice
(`realtime-test/` is Node, `turkish-nlp` is Python). Async I/O matters later
for the OpenAI Realtime API (WebSocket, Milestone 8) and the MCP server
(Milestone 11).

**Decision:** Python, with FastAPI as the web framework — async-native
(covers the later realtime/MCP needs), and gives request/response typing
that maps naturally onto `tools.md`'s function contract. Dependency
management via `uv` (already installed locally; fast, single tool for
venvs + deps + running scripts).

**Status:** Decided (2026-08-10).

---

## 10. Persistence: SQLite as the live store, with backups and a git-tracked flat-file export

**Context:** Milestone 0 needs a persistence approach for mistake/session/
profile data (`domain-model.md`). Considered flat files only (à la
`Language-Lab`'s `MISTAKES.md`/`PRACTICE_LOG.md`), SQLite only, or a
combination. Concern raised: SQLite is a binary file, so `git diff` on it
is useless even though `git checkout` still recovers a deleted/corrupted
file byte-for-byte — git alone doesn't give an inspectable audit trail.

**Decision:** SQLite is the live, queryable store the backend actually
reads/writes (fits `search_mistakes`-style precise querying that
`domain-model.md` asks for). Two things layered on top: (1) periodic
backups of the `.db` file for accidental-deletion protection, (2) a
git-tracked flat-file (Markdown/JSON) export written alongside normal
writes, giving a diffable human-readable history without making SQLite the
audit trail itself. Persistence stays isolated behind its own module
(per decision #2/#3's provider-resilience principle) so a future migration
to another SQL engine only touches that module, not callers of `tools.md`'s
functions.

**Status:** Decided (2026-08-10).

---

## 11. Backend runs as a local process during initial development

**Context:** Milestone 0 needs to decide where the backend runs to start
development — doesn't need to be the final answer per `milestones.md`.

**Decision:** Local process (`uv run`) for now, not containerized.
Simplest path to a running Milestone 0/1 scaffold; containerization can be
revisited once the vision doc's cross-device sync/portability goals are
actually being built toward.

**Status:** Decided (2026-08-10) — provisional, may revisit.
