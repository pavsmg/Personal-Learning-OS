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

---

## 12. `search_notes` uses naive weighted keyword/token scoring, no external search library or embeddings

**Context:** `retrieval.md` deliberately left retrieval technology an open
question at project inception ("no specific retrieval technology has been
chosen yet"). Milestone 2 needed a concrete `search_notes` implementation to
validate against the real vault.

**Decision:** In-process scoring over the whole loaded vault: tokenize the
query, score each note by (exact-phrase title match bonus) + weighted
per-token counts across title/tags/body, no external search library (no
SQLite FTS, no Whoosh) and no embeddings/vector search. Swappable later
behind the same `search_notes(query)` signature per the provider-resilience
principle (#2) — callers never see the scoring internals.

**Status:** Decided (2026-08-10) — interim/provisional, same as #11. This
resolves only the keyword-search half of `retrieval.md`'s open question;
embeddings/semantic search remains open, to revisit once real conversational
sessions (Milestone 5) exercise search quality against real usage.

---

## 13. Tool-calling contract represented as an in-process registry (`Tool` dataclass + `TOOLS` dict + `call_tool`)

**Context:** Milestone 3 needed to turn `tools.md`'s prose function list into
actual code: something a future caller (Milestone 7's Realtime integration,
Milestone 11's MCP server) can look up by name and invoke, not just 18
independently-typed Python functions with no common handle.

**Decision:** `tools_interface/registry.py` defines a minimal `Tool`
dataclass (name, description, handler), a `TOOLS: dict[str, Tool]` populated
at import time, and `call_tool(name, **kwargs)` for dispatch. Deliberately
no JSON-schema generation or pydantic-model-per-parameter validation layer
yet — that's real work with a real consumer at Milestone 7/10, not needed to
satisfy this milestone's "one consistent interface" requirement, and
building it now would be guessing at a shape those milestones haven't
determined yet. Structured return types (`MistakeEntry`, `SessionPlan`/
`SessionSummary`, `MasteryEstimate`, `JobFitAnalysis`) use pydantic
`BaseModel` for free JSON serialization later, matching `retrieval/models.py`'s
existing pattern.

Also decided: `mistakes/` and `sessions/` each got a real `service.py` (typed
stub functions raising `NotImplementedError`, living in the module their
future real implementation will occupy) since Milestone 1 already created
those folders. Progression, Language module, Stats, and Career have no
module folder yet — no milestone has created one — so their stubs live
provisionally in `tools_interface/stubs.py` rather than inventing new module
boundaries this milestone wasn't scoped to decide.

**Status:** Partially superseded by #14 — the "real consumer at Milestone
7/10" assumption was wrong. Milestone 5's own text chat loop needed
JSON-schema generation immediately (OpenAI's function-calling requires a
JSON Schema per tool), so `Tool.parameters_schema` was added there instead,
computed automatically via introspection at `register()` time with no
changes needed to any call site. The registry/dispatch design itself
(`Tool`, `TOOLS`, `call_tool`) is otherwise unchanged and still Decided.

---

## 14. OpenAI Chat Completions for Milestone 5's text-only conversations

**Context:** Milestone 5 needed a concrete text-capable LLM to wire the
planner/retrieval/tool-calling loop against. User had a working
`OPENAI_API_KEY` already (used earlier this session), and `decisions.md` #5
already picked OpenAI for the later Realtime voice API (Milestone 7) — user
chose to keep one provider through both, though `architecture.md`'s
provider-resilience principle doesn't require that (`llm_client.py` is the
only file that touches the OpenAI SDK's response shape; the rest of
`conversation/loop.py` works against a provider-agnostic `LLMReply` type).

**Decision:** OpenAI Chat Completions API via the official `openai` SDK.
Model is configurable (`Settings.openai_model`, `OPENAI_MODEL` env var),
defaulting to `gpt-5.4-mini` — checked against the live API
(`client.models.list()`) rather than assumed, and confirmed to support
function-calling with a real test call before committing to it. Only the 3
real retrieval tools (`search_notes`/`get_note`/`related_notes`) are exposed
to the model during conversation; `create_session`/`finish_session`/
`summarize_session` are backend-orchestrated around the conversation, not
model-callable tools, so session lifecycle stays a backend decision.

**Status:** Decided (2026-08-10).

---

## 15. Mastery scope narrowed to conceptual understanding, not overall competence

**Context:** `pedagogy.md`'s "Illusion of competence from conversational
fluency" risk (conversational fluency is a bad proxy for durable/applied
learning) was flagged but never resolved into a concrete, honestly-scoped
goal — `vision.md`'s "current level per domain" language and the single
`mastery: float` field on `MasteryEstimate` (`tools_interface/models.py`)
both implicitly claimed to assess overall competence, which conversational
testing can't reliably do.

**Decision:** Recalibrate the system's stated goal across `pedagogy.md`,
`vision.md`, and `domain-model.md`: what conversational testing honestly
verifies is conceptual/declarative understanding (definitions, mechanisms,
distinctions between related ideas), not applied/practical competence
(solving novel problems, executing a skill under real conditions). Docs
updated to state this explicitly rather than leaving the risk flagged but
unaddressed. Code implication, not yet acted on: `MasteryEstimate.mastery:
float` is a single blended score and doesn't reflect this distinction —
flagged in `domain-model.md` as something to resolve before `estimate_mastery`
(Milestone 6) is actually implemented, rather than changing the schema now
ahead of a real consumer (the session planner) that should drive its
final shape.

**Status:** Decided (2026-08-10).

---

## 16. Session planner formalized as two explicit modes: automatic proposal vs. learner-directed topic

**Context:** `learning-engine.md` described the planner as if it always
decides the session unilaterally ("a planner decides the day's
objective..."), but the actually-implemented `create_session(topic: str,
...)` (Milestone 4, done) requires a topic — the reverse gap: docs implied
fully automatic, code only supports learner-directed. User asked to make
both paths explicit: the planner can either propose a session automatically
or build one around a topic the learner names.

**Decision:** `learning-engine.md` now documents two explicit modes,
automatic and learner-directed, both producing the same `SessionPlan` and
entering the same conversation flow — the difference is only in how the
objective/concepts get selected. Mode selection is a backend/orchestration
choice made before the conversation starts, consistent with `create_session`
being backend-orchestrated rather than model-callable (#14). Code
implication for Milestone 6: `create_session`'s `topic` parameter becomes
optional (`topic: str | None = None`), falling back to `recommend_review`'s
picks when omitted — added as an explicit sub-task under Milestone 6 in
`milestones.md` rather than left implicit inside "wire recommend_review back
into the planner."

**Status:** Decided (2026-08-10).

---

## 17. Milestone 6: SQLite persistence, resolved schemas, and where Progression logic lives

**Context:** Milestone 6 needed to turn `save_mistake`/`search_mistakes`/
`get_recent_mistakes`/`get_learning_profile`/`estimate_mastery`/
`recommend_review` from stubs into real logic, and two things #15/#16 had
flagged but not yet acted on needed resolving in the process, not deferred
again.

**Decisions:**
- **Persistence:** real SQLite via stdlib `sqlite3` (no new dependency),
  fulfilling #10 for mistake data specifically — decided now rather than
  keeping mistakes in-memory (Milestone 5's precedent for sessions) because
  the DoD ("a mistake made in one session visibly changes what the next
  session's planner chooses to review") only means something if it survives
  past a single process, and #10 already committed to SQLite for exactly
  this data two milestones ago. `mistakes/store.py`; `Settings.db_path`
  (default `data/mistakes.db`, already covered by the existing `*.db`
  gitignore entry). Connections are opened fresh per call, not cached — no
  new cache-clearing needed in `conftest.py`.
- **`MistakeEntry` gains `domain: str`** (`mistakes/models.py`) — missing
  before despite `get_recent_mistakes`/`get_learning_profile`/
  `estimate_mastery` all needing to filter/group by it. Inferred once per
  session, server-side, not asked of the model as a free guess: anchor
  note's frontmatter `domain:` → its first vault tag → `"general"`. Same
  inference now also sets the new `SessionPlan.domain` field
  (`sessions/models.py`).
- **`MasteryEstimate` resolved per #15's flag**: `mastery: float` renamed to
  `conceptual_understanding: float`, plus a new `mistake_count: int`. The
  count is the actual fix, not the rename alone — a `1.0` with
  `mistake_count=0` is machine-readably "no signal yet," not "proven solid."
  Formula: `1.0 - average(confidence of recorded mistakes for that
  concept)`, clamped `[0, 1]`, defaulting to `1.0` with zero mistakes
  (documented limitation: this conflates "never tested" with "solid,"
  inherent to a mistake-only memory model per `domain-model.md`'s own
  framing — not something this milestone can fully solve, only state
  honestly). `MasteryEstimate` itself moved from `tools_interface/models.py`
  into `mistakes/models.py` (see below — avoids a circular import, and it's
  mistake-derived data anyway).
- **Progression functions moved into `mistakes/service.py`**, out of
  `tools_interface/stubs.py` — corrects part of #13's "provisional...
  pending their own module" placement. They're entirely computed from
  mistake data, so once that data is real, co-locating the computation with
  it is simpler than inventing a separate module. (This move is also what
  necessitated moving `MasteryEstimate` alongside them: `mistakes/service.py`
  needs it, and `mistakes` importing from `tools_interface` while
  `tools_interface/__init__.py` imports from `mistakes` would be a real
  circular import, not just an style preference.)
- **`corrected` stays `False` at save time.** It means "the learner has
  since demonstrated they understand this," not "the tutor explained the
  right answer" — the latter happens for every saved mistake by design,
  which would make the field meaningless if it defaulted `True`. Nothing in
  this milestone re-verifies and flips it; that's a real, explicitly scoped
  gap for a future milestone (some "confirm previously-flagged concept is
  now solid" mechanism), not a bug.
- **`save_mistake`'s `domain` argument is model-supplied**, guided by the
  system prompt to echo the session's actual domain, not backend-injected.
  Backend-injecting it would need session-context-aware tool dispatch,
  which `tools_interface.call_tool`'s generic `handler(**kwargs)` dispatch
  doesn't support today and no other tool needs yet — worth building if a
  second real need appears, not speculatively now. Worst case of trusting
  the model here is a slightly-off domain string on one entry: low-stakes,
  correctable later.
- **`CONVERSATION_TOOLS`** (`conversation/loop.py`) gains `save_mistake`
  (required — this is the actual detection-wiring) and
  `get_recent_mistakes` (lets the model check a domain's known gaps at
  session start, strengthening the existing "revisit shaky concepts" prompt
  rule with real persisted data instead of only in-conversation memory).

**Validated end-to-end with real data**, not just unit tests: one real
session flagged and saved a genuine `Adam optimizer` mistake (confirmed by
querying the live SQLite DB directly, not assumed); `create_session(topic=None)`
immediately afterward proposed that exact concept as the day's session. See
`milestones.md` Milestone 6 for the full transcript excerpt.

**Status:** Decided (2026-08-10).

---

## 18. Milestone 7: Career functions read the whole profile, use the LLM for semantic matching, and their own module

**Context:** `summarize_skills_for_cv()`/`analyze_job_fit(job_description)`
needed real implementations reading `mistakes/service.py`'s
`get_learning_profile`.

**Decisions:**
- **`get_learning_profile`'s `domain` param made optional**
  (`domain: str | None = None`), consistent with `get_recent_mistakes`/
  `recommend_review`'s existing pattern — `None` means all domains, grouped
  by `(domain, concept)` rather than just `concept` (a concept name could
  in principle repeat across domains, e.g. "Overfitting" in both
  classical-ml and statistics — group correctly rather than assume
  uniqueness).
- **Stated plainly, not discovered-and-hidden:** the mistake-only memory
  model means `get_learning_profile` can only surface concepts with at
  least one recorded mistake — a concept never gotten wrong is invisible to
  it entirely. `summarize_skills_for_cv` therefore can't claim to be a
  comprehensive skill inventory; it describes *concepts tested and shown
  solid understanding of*, and says so explicitly in its own output when
  coverage is thin (empty-strengths case), continuing #15's honesty
  standard. **Confirmed against real usage, not just reasoned about in the
  abstract:** all 3 mistakes produced by real conversation sessions came
  back high-confidence (correctly — they were genuine, clear errors), so
  *none* crossed the 0.7 strength threshold from live conversation data
  alone — `summarize_skills_for_cv()` correctly returned its honest
  no-data message against real data before any strength existed. A fourth
  entry was added directly (not conversation-triggered) with a
  deliberately low confidence (0.15, simulating a minor/trivial slip) to
  also exercise and confirm the populated-strengths path against a real
  LLM call, which returned appropriately scoped CV language ("demonstrated
  understanding of optimizers through tracked review... during tutoring
  sessions" — not overclaiming production experience).
- **Both functions call the LLM** (`llm_client.chat_completion`, extended
  with an optional `tool_choice` param for `analyze_job_fit`'s forced
  structured output) — unlike Milestone 5's `summarize_session`, which
  deliberately stayed naive/non-LLM because it only needed literal
  substring matching against a small known concept list. Matching a job
  posting's free-form prose against tracked concepts is a genuinely
  different, open-ended semantic task naive keyword matching would do
  badly at; recognizing that difference (rather than applying the same
  "keep it naive" precedent everywhere by default) is the actual judgment
  call here. **Confirmed against a real posting**: the model correctly
  distinguished "topic touched but weak" (`Gradient descent`, `Adam
  optimizer`, `Turkish alphabet` — all real tracked entries with low
  conceptual_understanding) from "topic touched and strong" (`Optimizer`),
  folding the former into the gap description rather than forcing a false
  strength match — not hallucinated relevance.
- **New `career/` module** (`models.py`/`prompt.py`/`service.py`/`cli.py`),
  following Milestone 6's exact precedent for Progression: implement for
  real, move out of `tools_interface/stubs.py` into a real module.
  `JobFitAnalysis` moved from `tools_interface/models.py` into
  `career/models.py` (that file is now deleted — it held nothing else).
- **Structural fix, not an import-order workaround:** `llm_client.py`
  moved from `conversation/` to top-level `learning_os/llm_client.py`.
  `career/service.py` needing `chat_completion` created a real cycle
  (`tools_interface` → `career` → `conversation` (via `llm_client`) →
  `tools_interface`, since importing any submodule of `conversation` forces
  `conversation/__init__.py` to run first, which imports `loop.py`, which
  needs `tools_interface`) — fixed by recognizing `llm_client` is genuinely
  shared infrastructure now, not conversation-specific, so it shouldn't
  live nested inside a package only one of its two consumers belongs to.
  `to_openai_tools` (which only `loop.py` ever calls) moved into
  `conversation/loop.py` itself rather than travelling with the client.
- **Registry gained an internal-parameter convention:** both Career
  functions take an injectable `_chat_fn` (leading underscore) for test
  dependency injection, mirroring `conversation/loop.py`'s existing
  `chat_fn` pattern. Since these functions are registered tools, their
  parameters get auto-converted to JSON Schema (`decisions.md` #13's
  correction) — but a `Callable` parameter isn't JSON-Schema-representable,
  which surfaced immediately as a real `PydanticInvalidForJsonSchema` error
  on import, not a theoretical concern. Fix: `tools_interface/registry.py`'s
  `_schema_for` now skips any parameter whose name starts with `_` —
  a reusable convention for "internal, not model-facing" rather than a
  one-off special case for this parameter.

**Status:** Decided (2026-08-10).

---

## 19. Pedagogy gate (per `roadmap.md`, before Milestone 8/voice): GO, with two logged non-blocking notes

**Context:** `roadmap.md`/`pedagogy.md` both gate voice work (Milestone 8)
on re-checking `pedagogy.md`'s realistic goals against everything built
across Milestones 1–7 before sinking effort into realtime audio on top of
a loop that hasn't been checked. Milestone 5's own pedagogy check-in
already did a first-pass version of this (3–4 sessions, found and fixed one
real correction-drift gap); this gate reviews more broadly across all ~7
real sessions run since (M5–M7), asks for an explicit decision, not just
another check-in note.

**Review, against `pedagogy.md`'s four "realistic goals" criteria:**

- **Does the agent actually test recall, not just discuss? — Yes,
  consistently, across every real session run so far.** Every session
  opened with a question, not a lecture. Real corrections observed:
  `Adam optimizer` ("just faster gradient descent" → corrected with real
  note wording, twice across M5 and M6 validation runs), `Turkish alphabet`
  (three separate wrong claims corrected in-turn across two different real
  runs, each grounded in the note's actual letter count/pronunciation
  facts), `Gradient descent` ("always finds the global minimum" → corrected
  immediately, *and* the session's closing explicitly circled back to that
  exact shaky point before wrapping — rule 6, "revisit shaky concepts,"
  working exactly as designed, not just as a hope). The one real gap found
  (Milestone 5: a wrong claim hedged as "...right?" could slide by
  uncorrected) was fixed in `prompt.py` and re-verified against the *same*
  failing case, not just assumed fixed.
- **Conceptual understanding, not overall competence — honored in what the
  system actually outputs, not just in the docs.** Real
  `summarize_skills_for_cv` output: "Demonstrated understanding of
  optimizers *through tracked review*... *during tutoring sessions*" — not
  "proficient in" or "experienced with." The scoping ADR #15 asked for
  shows up in real generated text, not only in `domain-model.md`'s prose.
- **Consistency over the baseline — not yet assessable, correctly not
  being forced.** All real sessions so far are agent-run validation, not
  longitudinal personal usage; `pedagogy.md` itself says this needs usage
  history an MVP won't have yet. Nothing to report here is itself the
  correct state at this stage — flagging it as still open, not silently
  skipping it.
- **Don't chase retention metrics prematurely — correctly not attempted.**
  Validation stayed behavioral (is it testing recall) throughout, per
  `pedagogy.md`'s own instruction.

**Two non-blocking notes, logged rather than silently dropped:**

1. **Cross-domain interleaving isn't actually implemented.**
   `pedagogy.md`'s "Cross-domain breadth vs. depth" risk says interleaving
   only helps "if the retrieval and planning layers actually mix domains
   rather than defaulting to single-topic sessions" — checked against real
   behavior, not assumed: `create_session("Gradient descent")` returns
   `['Gradient descent', 'Adam optimizer', 'algorithm', 'ANN',
   'backpropagation']` — every concept from the same neighborhood,
   `related_notes`' 1-hop expansion never leaves the anchor's domain in
   practice. `vision.md`'s cross-domain ambition and the current planner's
   naive single-topic-anchor heuristic (Milestone 4, still a "v1, doesn't
   need to be smart" implementation) don't match yet. Not a recall-testing
   problem (that's solid, per above) and not something voice work makes
   worse — a session-planner quality gap, worth a future backlog item
   (interleave a second, unrelated domain's due-for-review concept into a
   session rather than only expanding the anchor's own neighborhood), not
   a blocker for Milestone 8.
2. Carried forward from Milestones 6–7, unchanged: `MistakeEntry.corrected`
   never flips `True`; `save_mistake`'s `domain` is model-supplied, not
   backend-verified.

**Decision: GO.** Text-only pedagogical foundation (recall-testing,
honest scope, mistake-memory feedback loop) is solid enough, checked
against real usage rather than assumed, to build Milestone 8's voice
integration on top of. Neither non-blocking note above is a recall-testing
defect — they're scoped, known limitations, not silently-accepted risk.

**Status:** Decided (2026-08-11).

---

## 20. Milestone 8: use the SDK's built-in Realtime client, flat tool shape, text-input validation, M8/M9 scope split

**Context:** `roadmap.md` step 8 needed a working OpenAI Realtime API
integration: connect, configure a session, wire the tool contract into its
function-calling shape, handle voice/modalities/barge-in.

**Decisions:**
- **Use `openai`'s built-in `client.realtime.connect(model=...)`**
  (already present in the installed SDK, 2.53.0 — confirmed by reading
  `openai/resources/realtime/realtime.py` and `openai/types/realtime/*`
  directly, not assumed) rather than hand-rolling WebSocket code the way
  `Language-Lab/realtime-test/index.js` does. Gives a typed async
  connection (`connection.session`/`.response`/`.input_audio_buffer`/
  `.conversation.item`, `async for event in connection`) — eliminates most
  of the protocol-level risk a raw implementation would carry.
  `Language-Lab`'s script remained the reference for the *audio pipeline*
  only (PipeWire echo-cancel + `parec`/`paplay`), ported to Python via
  `asyncio.create_subprocess_exec` in `realtime/audio.py` — confirmed this
  environment actually has that stack and real audio hardware
  (`pactl list short sinks/sources`) before relying on it.
- **The Realtime API's function-tool shape is flat** —
  `{"type":"function","name":,"description":,"parameters":}` — unlike Chat
  Completions' nested envelope (`conversation/loop.py`'s `to_openai_tools`).
  New `realtime/tools.py:to_realtime_tools` handles this envelope
  specifically; confirmed via `RealtimeFunctionToolParam` before writing
  any code, and confirmed again live (`session.updated`'s `tools` echoed
  back with real `name` attributes, not dict keys — required an attribute-
  access fix during validation, not a design change).
- **`serialize_for_json`/`to_json` extracted** from `conversation/loop.py`
  into top-level `learning_os/serialization.py` — both the text and
  realtime loops need to turn a tool result (a pydantic model or list of
  them) into a JSON string for their respective wire formats. Pure
  extraction, no behavior change (`test_conversation_loop.py` passed
  unchanged after).
- **Scope split from Milestone 9, stated explicitly**: `REALTIME_TOOLS =
  ["search_notes", "get_note", "related_notes"]` only — `save_mistake`,
  `get_recent_mistakes`, `finish_session`, `summarize_session`, and
  transcript recording are *not* wired into the realtime loop.
  `roadmap.md` already phases this as Milestone 9's "port the full session
  loop... from text to voice" — Milestone 8 stays a protocol/tool-calling
  proof, not a feature port, so it doesn't overlap M9's explicit task.
- **Validation used text input, not real human speech** — stated as a
  real constraint, not glossed over: nothing about this milestone lets an
  AI assistant produce genuine spoken audio input or perceive real speaker
  output. The Realtime API accepts text (`conversation.item.create` with
  `input_text`) in the same live session while still producing real audio
  *output*, so the protocol/tool-calling/audio-generation path got a real
  end-to-end check without needing a human. Confirmed live: a real
  `search_notes` → `get_note` tool chain (the model chose to call both
  before answering, unprompted), a real transcript ("Gradient descent is
  an optimization algorithm... Now, how would you explain what the
  gradient is?" — the *same* teacher-style prompt rules from
  `conversation/prompt.py` carried over correctly, including asking a
  follow-up rather than just answering), and 477,600 bytes of real PCM16
  24kHz audio, verified as a valid WAV (not just assumed non-empty).
  Separately, confirmed the `pactl`/`parec` subprocess plumbing itself
  spawns and captures real bytes (echo-cancel module loads, mic captures,
  clean unload verified via `pactl list` afterward showing no leftover
  virtual devices) — not a substitute for a real spoken exchange, just
  confirmation the mechanism Milestone 9 depends on isn't broken. A true
  human-voice round trip is Milestone 9's explicit "run at least 3 full
  voice sessions," or something to try directly now since real hardware is
  present (`uv run learning-os-voice`).
- **Barge-in improves on the reference script**: on
  `input_audio_buffer.speech_started` while a response is in progress,
  `realtime/loop.py` calls `connection.response.cancel()` (stops server-
  side generation) *and* `speaker.restart()` (cuts local playback) —
  `Language-Lab`'s script only did the local-playback half.
- **Config**: `openai_realtime_model` (default `gpt-realtime-mini`,
  verified against the live model list before trusting it, same discipline
  as #9/#14) and `openai_realtime_voice` (default `marin` — the SDK's own
  docstring recommends `marin`/`cedar` for best quality).

**Status:** Decided (2026-08-11).
