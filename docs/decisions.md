# Decisions

Architecture Decision Record log. Every nontrivial choice made on this
project gets an entry here, written when the choice is made — not
reconstructed after the fact. Format: Context / Decision / Status.

Entries 1–7 below are seeded from the original brainstorming conversation
(2026-08-05) that produced this project's vision. They were originally
marked **Proposed** rather than **Decided**, pending confirmation once the
relevant part of the roadmap was actually reached rather than treated as
locked in from day one. As of Milestone 11 (2026-08-11), all of 1–6 have
been built against and confirmed — see each entry's Status line for what
actually happened.

---

## 1. Backend owns domain logic; the model only handles conversation and tool selection

**Context:** Deciding where retrieval, mastery calculation, session
planning, spaced repetition, memory storage, and scheduling should live —
in the LLM's prompt/reasoning, or in backend code the LLM calls into.

**Decision:** All of that logic lives in the backend as durable,
provider-independent code (`architecture.md`). The model's job is limited
to conversation, reasoning, explanation, tone, and deciding which tool to
call.

**Status:** Decided (2026-08-11) — confirmed by Milestone 11: mastery
calculation, session planning, and mistake persistence have stayed
backend-only through 11 milestones and three different consumers (text
loop, voice loop, MCP server), with no logic duplicated into any of them.

---

## 2. Provider resilience extends to every component, not just the conversation layer

**Context:** `Language-Lab` already has a "provider independence"
principle, but scoped only to the real-time conversation provider.

**Decision:** Extend the same principle to every component — voice model,
LLM, transcription engine, embedding engine, search engine. Each must be
swappable without touching durable data (knowledge, mistakes, progression).

**Status:** Decided (2026-08-11) — confirmed for the LLM (Chat Completions
vs. Realtime, #14/#20) and the voice provider (#5) so far, both isolated
behind the tool contract with no durable-data coupling. Search-engine and
embedding-engine swappability is unexercised so far (`search_notes` has
only ever had one implementation, #12) — the principle stands as a
constraint on new code, not yet validated by an actual swap for those two.
Milestone 12 (a second realtime voice provider) is the next real test.

---

## 3. Modular architecture, one module per capability

**Context:** Needed a structure that supports building incrementally and
replacing any one component per decision #2.

**Decision:** Separate modules for knowledge retrieval, error retrieval,
session planning, question generation, real-time conversation, evaluation,
memory, sync, transcription, conversation analysis, plus the existing
Language-Lab module.

**Status:** Decided (2026-08-11) — confirmed by the actual package layout
(`retrieval/`, `sessions/`, `mistakes/`, `career/`, `realtime/`,
`language/`, `mcp_server/`, `conversation/`), each with a single
capability and no cross-module reach-in beyond the shared
`tools_interface` contract.

---

## 4. MCP exposure deferred past the voice MVP

**Context:** MCP would let other AI surfaces (Claude Code, Claude Desktop,
Cursor) query the learning engine directly. But the OpenAI Realtime API's
function calling doesn't go through MCP, so it adds nothing to the voice
loop itself.

**Decision:** Build the voice MVP first; MCP server is a later-stage
addition (`mcp.md`), valuable for secondary non-voice clients, not core to
initial build.

**Status:** Decided (2026-08-11) — built as Milestone 11, after the voice
MVP (Milestones 8–9) as planned. See #24 for the implementation record.

---

## 5. OpenAI Realtime API as the initial voice provider

**Context:** Needed a concrete first real-time voice provider to start
building/testing against. `Language-Lab` already uses ElevenLabs for its
own conversational agents.

**Decision:** Start with the OpenAI Realtime API (low latency, WebRTC,
interruptions, function calling) — deliberately a different choice from
Language-Lab's ElevenLabs, and explicitly a starting point for
experimentation, not a permanent commitment (see decision #2).

**Status:** Decided (2026-08-11) — built as Milestones 8–9, confirmed
working for real voice conversations. Still the only provider integrated;
evaluating a second one is Milestone 12, currently blocked on the user
not having a second provider's API key.

---

## 6. Text-first build order

**Context:** Realtime audio adds meaningful complexity (latency,
interruption handling, transcription) on top of the core learning-engine
logic.

**Decision:** Validate the learning engine and tool-calling loop over
text-only conversations first (`roadmap.md`, steps 1–7) before adding
voice (steps 8–9).

**Status:** Decided (2026-08-11) — followed as built: Milestones 1–7 were
all text-only, and the pedagogy gate (#19) was passed before voice work
(Milestones 8–9) started, exactly as this decision required.

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

---

## 21. Per-session transcript + tool-call log for the voice loop (follow-up to Milestone 8)

**Context:** User actually ran `learning-os-voice` for real and asked
whether there was any way to review a session's transcript or which tools
got called — there wasn't. `realtime/loop.py` printed live status
(`[listening...]`, spoken transcript deltas) but never recorded anything,
and never printed tool-call activity at all (an oversight, not a documented
scope decision, unlike transcript *persistence into the domain model*,
which is genuinely Milestone 9's job).

**Decision:** New `realtime/session_log.py`'s `SessionLog` — a plain-text,
timestamped, per-session log at `logs/<session_id>.log` (relative,
gitignored, mirrors `data/mistakes.db`'s convention), recording session
start (domain/objective/concepts), each user/assistant turn, tool calls
(name, arguments, full output), and errors. `realtime/loop.py` also now
prints tool-call activity live, not just to the file. Explicitly **not**
the same thing as Milestone 9's `record_turn`/`summarize_session` wiring —
this is a local human-readable convenience log, not domain-model
persistence; Milestone 9 still needs to do its own job when it lands.

Side effect worth recording: creating a real `backend/.env` (to fix the
user's `vault_path` config error) exposed a fragile test —
`test_health_reports_ok_without_config` assumed no `.env` file existed on
disk to prove the "no config" path, which broke the moment a real one did.
Fixed by running that test from an empty `tmp_path` directory
(`monkeypatch.chdir`) so it's isolated from real developer-machine state,
not by deleting the `.env` file it was implicitly depending on the absence
of.

**Status:** Decided (2026-08-11).

---

## 22. Milestone 9: real voice parity confirmed for correction/planning; a genuine, evidence-based gap for mistake persistence, documented not silently accepted

**Context:** Milestone 9 ported the rest of the text loop onto voice —
`TUTORING_TOOLS` (shared with text, closing a drift risk where
`realtime/loop.py`'s tool list had gone stale after Milestone 6 added
`save_mistake`/`get_recent_mistakes` to text but not voice), `record_turn`
transcript recording, and `finish_session`/`summarize_session` in the
event loop's `finally` block. Deliberately did not replicate text's
`END_SESSION_NUDGE` mechanic — no clean signal channel exists for it in
voice without real added complexity, and it's not filling a real gap: the
system prompt's rule 6 ("circle back to shaky concepts") already fires
proactively, confirmed directly in real Milestone 6 transcripts before
this milestone even started.

**Real validation, 5 real sessions total (3 required + 2 diagnostic):**

- **Full parity confirmed**: conversational mistake correction, 4/4 —
  every deliberately wrong claim got caught and corrected in-turn,
  grounded in real note content, matching text's behavior exactly.
  Transcript recording → real `SessionSummary` output. Automatic mode
  (`topic=None`) correctly called `recommend_review()` and picked
  `Turkish alphabet` — the actual weakest tracked concept — confirming
  Milestone 6's planner-feedback loop works identically when driven
  through voice, not just text.
- **Real gap found, not fixed, documented instead**: `save_mistake` never
  fired — confirmed via direct SQLite row-count check (not assumed) across
  **4 separate real attempts**: the original prompt, a substantially
  strengthened "mandatory, not optional" rewrite of rule 3, and tested
  against both `gpt-realtime-mini` and the full `gpt-realtime` model —
  same null result every time. The same instructions reliably triggered
  `save_mistake` via Chat Completions (text mode, Milestones 6–7). This
  looks like a genuine Realtime-API characteristic — plausibly that
  audio-generating models deprioritize "side-effect" tool calls (not
  needed to answer the user in the moment) in favor of continuous spoken
  flow — not something two targeted prompt/model fix attempts could
  resolve. **User decision: document as a known, unresolved limitation
  rather than pursue a backend-triggered heuristic nudge now** (uncertain
  payoff against what may be a model-level tendency, more open-ended real
  API cost). The strengthened rule 3 wording stays (a strictly clearer
  instruction, harmless for text mode where it already worked, may help
  future realtime model versions or real spoken-audio input rather than
  the text-input validation substitute used here).

**Practical consequence, stated plainly**: mistakes made and corrected in
a real spoken session are *not* currently being persisted to
`mistakes.db`, so they won't inform `recommend_review`/`estimate_mastery`
the way a text session's mistakes do. Voice sessions today: real teaching
loop, not yet a real memory loop. This is the concrete scope of "not full
parity" — everything else checked out identical to text.

**Status:** Decided (2026-08-11) — the persistence gap is open, tracked
here and in `milestones.md`, not silently dropped.

---

## 23. Milestone 10: import Language-Lab mistakes as real `MistakeEntry` rows, not a read-only adapter

**Context:** `milestones.md` explicitly asked for a logged decision:
read `Language-Lab`'s tracked files (`ROADMAP.md`/`MISTAKES.md`/
`PRACTICE_LOG.md`) directly, or build an adapter into this project's own
`domain-model.md` schema. My first pass (during planning) concluded
"read directly, never convert" — `Status: Active/Watching/Resolved` and no
per-entry timestamp don't map cleanly onto `MistakeEntry`'s typed
`confidence: float`/`timestamp: datetime`, and forcing it seemed like
fabricating precision the source data doesn't have.

**The user pushed back, correctly, and the decision reversed before any
code was written**: the Language-Lab data that exists today is test
entries, not real accumulated practice history — nothing precious to
preserve exactly-as-is. Treating it as a permanently-separate read-only
lookup would throw away real value a conversion gives for free: imported
as real `MistakeEntry` rows, language mistakes compete in the *same*
`recommend_review` scheduling as vault-domain mistakes, and become visible
to Career/CV coaching (`get_learning_profile`) — neither of which a
read-only adapter provides. This also matches `decisions.md` #7's actual
stated intent better than my first pass did: "Language-Lab gets
integrated... rather than rebuilt from scratch," meaning its separate
mistake-tracking is meant to be *absorbed*, not kept parallel forever.

**Decision**: `language/importer.py` imports `MISTAKES.md` into
`mistakes.db` via the existing, unmodified `save_mistake` (domain = the
language name, lowercase). Mapping, agreed with the user as reasonable-for-now
("applies for knowledge no matter the domain," not language-specific,
free to revise later):
- `confidence`: `Active → 0.7`, `Watching → 0.4`, `Resolved → 0.1`.
- `severity`: `seen_count >= 2 → "moderate"`, else `"minor"` — a real
  signal already in the source data (a pattern confirmed twice is more
  entrenched), not invented.
- `corrected` stays `False` for all imports (including `Resolved` ones) —
  deliberately not threading a way to override `save_mistake`'s existing
  behavior, since `corrected` doesn't feed `estimate_mastery`'s math today
  (only `confidence` does — `decisions.md` #17); a `Resolved` entry's low
  confidence (`0.1`) already produces a correctly-high
  `conceptual_understanding` without it.
- Idempotent by design: checks `get_learning_profile(domain=language)` for
  an existing same-named concept before inserting, so re-running as
  Language-Lab's files change over time is always safe, not a one-shot
  migration.
`ROADMAP.md` (syllabus/coverage status) and `PRACTICE_LOG.md` (session
narrative) stay live reads via `get_curriculum`/`get_language_profile`'s
`recent_practice` field — genuinely not mistakes, no schema conflict, no
reason to force them into a typed store.

**Known limitation, flagged rather than fixed or silently ignored**:
`sessions/service.py`'s `_infer_domain` derives domain from the vault's
generic `#languages` tag (confirmed: the vault's own `CLAUDE.md` tags
*every* language with one shared tag, not per-language), so a *new*
mistake caught during a vault-triggered session (e.g.
`create_session("Turkish alphabet")`) lands in `domain="languages"`, not
`domain="turkish"` — it won't automatically join the same bucket this
import created unless the model happens to pass a specific language
string to `save_mistake` on its own. Fixing `_infer_domain` to detect a
specific language is real, separate work, out of this milestone's scope —
noted honestly, not patched over.

**Validated for real, not assumed**: `uv run learning-os-language-import`
against the actual `mistakes.db` imported exactly 6 English entries (the
only language with real data), confirmed idempotent (0 imported on
re-run). `recommend_review()` with no domain filter afterward returned
language concepts interleaved with vault-domain ones by weakness, proving
the "same scheduling loop" claim isn't theoretical. A real conversation
session (inspecting `state.messages` directly, not inferring from prose)
confirmed the model actually called `get_language_profile("English")` and
`get_curriculum("English")`, and the real imported data (the "make +
object" pattern, "Grammar Precision — In progress") directly shaped its
opening question.

**Status:** Decided (2026-08-11).

---

## 24. Milestone 11: MCP server as a generic, thin transport layer over `tools_interface.TOOLS`

**Context:** `mcp.md` scopes this milestone explicitly: "a thin transport
layer over the same `tools.md` function contract, not a separate
interface to design and maintain." The official `mcp` Python SDK is at
major version **2.0.0** — my own recollection of its API (`FastMCP`,
decorator-based registration) predates that major bump and was treated as
unverified going in, the same discipline Milestone 8 used for the
Realtime SDK. Checking the actually-installed source (not memory)
confirmed there is no `FastMCP` in 2.0.0 at all: the real API is
`mcp.server.MCPServer`, constructed with `name=`/`description=`, with an
`add_tool(fn, name=, description=)` method that introspects a real
callable's signature via `inspect.signature(fn, eval_str=True)` rather
than taking an explicit JSON-schema parameter.

**Decision:** `mcp_server/server.py` builds one `MCPServer` and registers
all 18 `tools_interface.TOOLS` entries in a single generic loop over
`TOOLS.items()` — not 18 hand-written wrappers. Each registered callable
is a thin `wrapper(**kwargs) -> call_tool(name, **kwargs)`, routing every
call through the existing, unmodified dispatcher. Per-tool special-casing
would have violated `mcp.md`'s "no new logic" framing directly, so the
loop being fully generic is the actual test of whether the design held,
not just a style preference. All 18 tools — including the two still-stub
functions (`retrieve_vocabulary`, `get_learning_statistics`) — are
exposed identically; a client calling a stub gets a real
`is_error=True` MCP result carrying the `NotImplementedError` message,
not a silently faked success or a filtered-out tool list. Runs over
**stdio** (`run(transport="stdio")`), the transport Claude Desktop/Code
actually use for locally-configured servers, not the HTTP/SSE variant
meant for remote servers.

**Real bug found and fixed, not designed around in advance:** two tools
(`summarize_skills_for_cv`, `analyze_job_fit`, from `career/service.py`)
take an internal `_chat_fn` parameter — a leading-underscore test-injection
hook that `tools_interface/registry.py`'s own schema generation already
excludes. MCP's `func_metadata()` raises `InvalidSignature` on *any*
leading-underscore parameter, rejecting the whole function outright. Fix:
`_public_wrapper()` computes the handler's real signature via
`inspect.signature(handler, eval_str=True)`, filters out
underscore-prefixed parameters, and sets the plain `wrapper`'s
`__signature__` attribute to the filtered result — `inspect.signature()`
(and therefore MCP's own introspection) respects a manually-set
`__signature__` directly. Applied uniformly to all 18 tools rather than
special-cased to the 2 affected ones, keeping the registration loop
generic.

**Validated for real, not assumed:** two independent real-protocol paths,
both via the SDK's own `ClientSession` (not a hand-rolled fake):
(1) `InMemoryTransport` — real server + real client speaking the real MCP
protocol over in-process streams, used for the offline pytest suite
(`tests/test_mcp_server.py`): confirms all 18 tools list with matching
descriptions, a real `search_notes` call against a synthetic vault
round-trips correctly serialized data, and `get_learning_statistics`
surfaces as a real MCP error, not a swallowed exception.
(2) A genuine OS subprocess: `stdio_client` spawning the actual
`uv run learning-os-mcp` entrypoint against the real vault
(`~/Documents/Obsidian-Digital-Brain`) and the real `mistakes.db` —
`search_notes("graph")` returned the real vault note, `get_recent_mistakes`
returned real imported mistake data from `decisions.md` #23's Language-Lab
import. This is the same DoD scenario `mcp.md` names ("what did I get
wrong on graph algorithms last week," asked from outside the voice app),
exercised end-to-end over the actual transport a secondary client would
use, not simulated.

**Status:** Decided (2026-08-11).

---

## 25. System prompt rule 10: disclose ungrounded concepts at the moment of quizzing, not on casual tangents

**Context:** Rule 5 already instructs the model to ground sessions in real
vault content via `search_notes`/`get_note`/`related_notes`, but nothing
tells it what to do when those tools come back empty for a concept — it
could silently answer from training data with the same confident tone as a
grounded answer, indistinguishable to the learner. Two concrete risks
this create: (1) no honesty signal when a learner asks about something
genuinely outside the vault, and (2) if the model then quizzes on and
corrects that ungrounded concept, a `save_mistake` call could log a
mistake whose `concept` doesn't match any real vault note title (violating
rule 3's own stated expectation), polluting `recommend_review`/
`estimate_mastery`/Career-coaching data with untraceable entries.

**Considered and rejected: disclosing on every ungrounded utterance.**
Flagging *any* topic outside the vault — including casual tangents ("how
does this compare to RMSProp?") — was rejected as real, not hypothetical,
friction: it conflicts with rule 4 (short, conversational, no lecturing)
and rule 8 (open naturally), and `pedagogy.md`'s own "friction risk"
section names exactly this failure mode — anything that makes the tool
feel naggier works against consistency of use, the metric the project's
own docs identify as the most realistically measurable early win. It would
also surface false positives often, since `search_notes` is naive
keyword/token scoring (`decisions.md` #12, no embeddings) — a real vault
note can fail to surface on off-phrasing, which would make the disclaimer
fire on content that does exist and teach distrust of the flag itself.

**Decision:** scope the check narrowly. New rule 10 in `prompt.py`: only
disclose when the model is about to *quiz* (test recall on) a concept —
not during casual discussion — and `search_notes`/`get_note` returned
nothing real for it. This is exactly the case where a false "verified"
signal would corrupt tracked data, so it's where the honesty cost is
worth paying; casual tangents don't get logged as mistakes either way, so
they don't need the disclaimer. Also added: never call `save_mistake` for
a concept flagged this way, closing the rule-3 concept-matching gap
directly rather than relying on the model to notice the conflict itself.

**Status:** Proposed (2026-08-12) — implemented in `prompt.py`, offline
test suite passes (128 tests, wiring-level only — nothing here exercises
real model behavior). Not yet validated against a real conversation the
way Milestone 5's pedagogy rules were (`decisions.md` entries for M5/M9
both required a real transcript showing the rule actually fires before
being called Decided). Needs: a real session where the learner raises a
concept genuinely absent from the vault mid-session, checked via
`--debug`/the session log to confirm `search_notes` actually returned
empty and the model disclosed rather than answered silently.

---

## 26. System prompt rule 11: require an applicative follow-up, not just a correct definition

**Context:** `pedagogy.md`'s own "Realistic goals" section already names this
as an explicit, accepted scope limit: the system verifies "conceptual
understanding... not whether \[the learner is] skilled at applying it
under real, unscripted conditions." Discussed with the user via a YouTube
video summarizing a popular (not peer-reviewed) taxonomy of thinking
modes — critical, abstract, applicative, systematic, associative,
convergent, divergent, lateral, holistic. Cross-checking that taxonomy
against the current prompt (`prompt.py`) showed the system exercises
essentially two of the nine (critical thinking via rule 2's
correct-or-not check; convergent thinking via the same recall-and-confirm
loop) and nothing that tests **applicative** thinking specifically —
transferring a correctly-recalled principle to a new situation. That gap
matches `pedagogy.md`'s own stated limitation exactly, which is what
made it worth acting on rather than treating as a novel claim from an
unvetted source.

**Explicitly not treated as evidence:** the video's framework is a
popular self-development taxonomy, not cited research — unlike
`pedagogy.md`'s own mechanisms (retrieval practice, spacing, generation
effect, desirable difficulty, interleaving), which are traceable to real
learning-science findings. It's used here only as an organizing lens that
happened to point at a gap the project's own docs had already flagged,
not as a new evidence source the design now depends on. The taxonomy
itself is logged as vault note `Modes of Thinking.md` (tagged
`#transconcept`, matching how the vault already tags cross-domain
recurring ideas like `Heuristic.md`) for the user's own reference — that
note is knowledge-base content, not something the system reads at
runtime.

**Decision:** new rule 11 in `prompt.py`. Once the learner correctly
explains a concept, the model must follow up at least once with a novel
scenario requiring application before treating the concept as covered —
not simply moving to the next item after a correct definition. Scoped as
a universal rule (not domain-gated) since applying a concept to a new
case is a generically useful check across every domain this project
covers, not a language-specific or ML-specific concern.

**Status:** Proposed (2026-08-12) — implemented in `prompt.py`, offline
test suite passes (131 tests, wiring-level only). Not yet validated
against a real conversation, same bar as rules 10 (`decisions.md` #25)
and the Milestone 5/9 pedagogy rules before them. Needs: a real session
where the learner gives a correct definition, checked (via `--debug`/the
session log or the transcript itself) for whether the model actually
poses an application scenario before moving on, rather than accepting the
definition and pivoting straight to the next concept.

---

## 27. Fix `parse_roadmap` truncating soft-wrapped status lines

**Context:** `language/loader.py`'s `parse_roadmap` matched `ROADMAP.md`
one physical line at a time via `ROADMAP_LINE_RE`. Real roadmap files
soft-wrap long status text onto an indented second line (e.g. `- 1.
Grammar Precision — In progress (adverb/adjective complement pattern` /
`  surfaced 2026-08-02)`) — the continuation line doesn't match the
`- N.` entry pattern, so it was silently skipped, truncating the status
mid-sentence with an unclosed parenthesis. Harmless while `get_curriculum`
was optional context for the model to glance at; became a real problem
once `decisions.md` #26/`sessions/service.py`'s planner fix started using
that output directly as `plan.concepts` in the system prompt.

**Decision:** `parse_roadmap` now tracks the current entry while
iterating and merges any indented, non-empty line following a matched
entry into that entry's status text, flushing on the next `- N.` match or
a blank/unindented line. Verified against the real English `ROADMAP.md`:
`create_session("ENGLISH ROADMAP")` now produces complete, unclosed-paren-free
concept strings.

**Status:** Decided (2026-08-12) — 133 tests pass, including two new
cases (`test_language_loader.py`): joining a soft-wrapped continuation,
and confirming an unindented trailing paragraph after the list doesn't
get merged in. Verified against real data, not just the synthetic
fixture.

---

## 28. Rule 10 refined: Language-Lab-sourced concepts are grounded, not vault-ungrounded

**Context:** First real session with `--debug` on since #25/#26 shipped
(topic "English"). Real, useful evidence: the planner fix (#26) worked —
the opening question came from a curriculum-sourced concept (`Vocabulary
Precision & False Friends`), not a generic vault note title — and rule 10
fired for the first time ever, disclosing honestly when asked for an
example. But the transcript also showed *why* it fired: the model called
`get_note` using the mistake-tracking label itself
(`'"capacities" used where "capabilities" is meant'`) as if it were a
vault note title. Confirmed against the real vault — no such note exists,
never will, because that label comes from `mistakes.db`/Language-Lab, not
the vault. So the `null` and the resulting "I don't have notes on that in
your vault" were technically true but misleading: the same session had
just opened by citing this *exact* tracked pattern via
`get_recent_mistakes`. Rule 10 (and rule 5, which pushes toward vault
grounding in the first place) were written assuming every "concept" is
vault-shaped — the planner fix in #26 broke that assumption on purpose,
and neither rule was updated to know the difference.

**Decision:** rule 5 now names the source explicitly per domain type —
vault tools for vault-anchored domains, rule 9's Language-Lab tools for
language domains — and states plainly that a curriculum/mistake label was
never going to match a vault note, so don't try. Rule 10 gets an explicit
carve-out: concepts already grounded via `get_language_profile`/
`get_curriculum`/`get_recent_mistakes` are real tracked data, not
vault-ungrounded, and shouldn't trigger the disclosure or a `get_note`
lookup at all.

**Status:** Proposed (2026-08-12) — same bar as #25/#26: this specific
wording hasn't been re-run against a real conversation yet. The
underlying honesty *mechanism* rule 10 implements is validated (it fired
correctly, on real evidence, in the session that exposed this gap) — but
this exact refined wording needs its own real check: a future English/
Language-Lab session should confirm the model no longer calls `get_note`
on a curriculum/mistake label, and doesn't disclose a vault gap for
concepts it already has real tracked data on.

---

## 29. Rule 1 amended: stop reformulating "how would you explain X" after the learner says they don't know

**Context:** Same real transcript that produced #28. After the learner
said "I really don't know the difference" between capacities/
capabilities, the model asked a reworded version of the same question
("in a sentence about an AI, would you say...") instead of explaining.
When the learner then explicitly asked "can you give an example to
distinguish the two?", the model still hadn't explained by the point the
transcript ended. User feedback, directly: this is "limiting and
honestly frustrating," and correctly identified the mechanism — rule 1
said "ask before you explain," full stop, with no exit condition for a
learner who has already told you they don't know. Retrieval practice (the
evidence `pedagogy.md` cites for ask-before-tell) only strengthens
material already encoded; it has nothing to operate on when the learner
has zero prior exposure to a specific vocabulary distinction. Continuing
to probe past an honest "I don't know" isn't testing recall, it's just
friction — and the user's broader point holds: vocabulary distinctions
especially can't be reasoned out from first principles the way a
mechanism (gradient descent, Adam) sometimes can; forcing guesswork at
an arbitrary word pair doesn't teach anything a direct explanation
wouldn't teach faster and more honestly.

**Decision:** rule 1 now treats "ask before tell" as one attempt, not a
loop. The first time the learner directly signals they don't know, the
model must stop reformulating and give a short, direct explanation
(ideally with a contrasting example) instead. Scoped as universal
(applies to any domain, not just language/vocabulary) since the
underlying problem — forcing production from someone with nothing to
produce from — isn't specific to vocabulary, though vocabulary is named
explicitly as the clearest case, per the user's own framing.

**Status:** Proposed (2026-08-12) — implemented in `prompt.py`, offline
suite passes (133 tests, wiring-level only). Needs a real re-run of a
similar scenario (a genuine "I don't know" on something the learner has
no prior exposure to) to confirm the model actually explains after one
signal instead of continuing to probe, same bar as #25/#26/#28.

---

## 30. Rule 5 amended: word-level vocabulary doesn't require a note or tracked entry to exist

**Context:** #29 fixed the *looping* symptom (ask-before-tell with no
exit), but the user pushed further, correctly identifying a second,
separate bug underneath it: rule 5 still framed grounding as something
every concept needs before the model can talk about it — a note for
vault domains, a Language-Lab entry for language domains. That's the
wrong model specifically for word-level vocabulary. In the user's own
words: "the vault's intention is never to be filled as if it was a
dictionary," and Language-Lab's tracked mistakes are only the subset of
vocabulary that has already surfaced as an error, not the full space of
words a learner might ask about. Requiring retrieval before explaining a
specific word pair means either (a) the model stalls or discloses a gap
for something it can already explain correctly from general knowledge, or
(b) the vault would need to grow a dedicated note per word to satisfy the
rule — exactly the "endless notes... to revolve around one word" the user
flagged as absurd. Distinct from #28: #28 fixed *disclosing* a false gap
for concepts genuinely already tracked elsewhere; this fixes the prior
assumption that word-level vocabulary needs to be tracked anywhere at all
before it can be explained.

**Decision:** rule 5 now states explicitly that it governs the session's
overall concepts, not every specific word raised inside one — a
vocabulary distinction doesn't need a note or tracked entry to exist
first; general language knowledge is the expected source for those, and
the model should explain directly rather than trying to retrieve or
disclose a gap. Rule 10 needed no further change: it was already scoped
to vault-anchored concepts only (per #28), so it was never firing on
language-domain vocabulary in the first place — the gap was entirely in
rule 5's implicit "ground everything" framing.

**Status:** Proposed (2026-08-12) — offline suite passes (133 tests).
Needs a real re-run: a fresh, previously-untracked vocabulary question in
a language session should get a direct explanation with no retrieval
attempt and no "I don't have notes on that" disclosure, same bar as
#25/#26/#28/#29.

---

## 31. Session planner: language-specific domain inference and curriculum-sourced concepts

**Context:** User reported a real, concrete pedagogy complaint: an
automatic-mode session opened by asking "how many letters does Turkish
have," which felt irrelevant to actually learning a language. Diagnosis,
via `--debug`: two stacked bugs. (1) `_infer_domain` derived domain from
a vault note's generic `#languages` tag rather than the specific
language, so a Turkish mistake was tagged domain `languages` — meaning
`get_language_profile("Turkish")`/`get_curriculum("Turkish")` could never
see it, and vice versa (this is the gap `decisions.md` #23 had already
named but never fixed). (2) `create_session`'s anchor+`related_notes`
heuristic treats every vault note title as an equally valid quiz target,
with no way to distinguish a reference note (`Turkish alphabet.md` — a
letter chart) from an actual practicable concept.

**Decision:** `_infer_domain` (`sessions/service.py`) now checks the
anchor note's title against the four tracked languages (`LANGUAGES`,
moved to `language/service.py` so both modules can share it) before
falling back to the generic tag. `create_session` sources `plan.concepts`
from `get_curriculum(language)` when real structured curriculum data
exists for that language, falling back to the original vault
anchor+`related_notes` heuristic when it doesn't (an honest "nothing
tracked yet" state, not a bug — Turkish's `ROADMAP.md` is still
unstructured prose as of this writing).

**Status:** Decided (2026-08-12) — validated twice over: structurally,
against real vault + Language-Lab data (3 new tests in
`test_sessions_service.py`; confirmed via direct script that
`create_session("Turkish alphabet")` now resolves `domain="turkish"`, and
`create_session("ENGLISH ROADMAP")` sources concepts from real curriculum
status); and behaviorally, in the real "English" session that later
exposed #28's finding — the opening question was genuinely
curriculum-sourced (`Vocabulary Precision & False Friends`), not a
generic vault note title. **Note:** implemented and tested earlier in
this same working session but not logged here at the time — added
retroactively while setting up `backlog.md`, per this doc's own rule that
every nontrivial choice gets an entry.

---

## 32. Real spaced-repetition scheduling for `recommend_review`

**Context:** First item off `backlog.md`'s improvement-ideas list.
`recommend_review` ranked purely by `1 - average(confidence)` — the
single worst-understood concept, globally, forever — despite
`MistakeEntry.timestamp` being recorded on every `save_mistake` call and
never read anywhere. `pedagogy.md` already claims spaced repetition is
implemented ("a spaced-repetition scheduler in different clothing"); it
wasn't, in the one place that actually drives what gets reviewed.

**Decision:** naive v1 interval model — `_review_interval_days` maps
understanding linearly onto 1–14 days (poorly understood → reviewed
again almost immediately; well understood → long gap). `_overdue_ratio`
divides real elapsed time by that interval: >1 means overdue, <1 means
not due yet, and the ratio itself (not a due/not-due split) is the sort
key, so a long-overdue well-understood concept can still outrank a
barely-overdue poorly-understood one — real spaced-repetition semantics,
not just "worst score wins." Concepts tied on urgency (most commonly:
several mistakes saved in the same real session, seconds apart) fall back
to raw understanding, worst first — the previous ranking, now demoted to
a tiebreak rather than the primary signal. `recommend_review` still
returns every tracked concept, just reordered — no filtering to
"due-only," so automatic-mode session planning doesn't start erroring
just because nothing is strictly overdue yet.

**Real bug caught during implementation, not just in review:** the first
version used raw (unrounded) elapsed time in the ratio. Two mistakes
saved seconds apart — the ordinary case, e.g. several corrections in one
session — got near-zero but essentially random relative orderings from
wall-clock/floating-point noise, which flipped the sign of an existing
passing test (`test_recommend_review_sorts_worst_first`) nondeterministically
between runs. Fixed by rounding `days_since` to the nearest whole day
before computing the ratio, so same-day entries genuinely tie instead of
racing — confirmed stable across 5 repeated real runs of the full test
file after the fix, not just a single passing run.

**Status:** Decided (2026-08-13) — 135 tests pass (2 new: equal
understanding at different recency ranks the older one first; a
long-overdue well-understood concept outranks a barely-overdue weak one,
the actual behavioral change this fix is supposed to produce). Verified
against the real `mistakes.db`: `Optimizer` (very well understood,
2 days old) and `"capacities" used where "capabilities" is meant`
(reviewed twice minutes ago) both correctly dropped toward the bottom of
`recommend_review()`'s real output, despite being tracked concepts,
because they're not actually due yet — the previous algorithm would have
ranked purely by confidence and ignored that entirely. This is a scheduling
fix, not a claim about live model behavior, so no real-conversation
recheck is needed the way prompt-rule changes require.

---

## 33. Domain-aware automatic mode: `recommend_domain()`

**Context:** Second item off `backlog.md`. Automatic-mode topic selection
(`create_session(topic=None)`) called `recommend_review()` with no domain
filter — a single global top-1 pick across every concept in every domain.
Even after #32's spacing fix, this has a real, distinct fairness gap: a
concept's `_overdue_ratio` is relative to its *own* interval, not an
absolute cross-domain urgency measure. A domain of consistently
hard-to-grasp concepts has structurally short intervals and will keep
generating fresh, quickly-recurring high ratios; a domain of easier
concepts has structurally longer intervals and takes proportionally
longer to climb back above 1.0 even when it's genuinely gone unreviewed —
biasing automatic mode toward "hard domains" or frequently-revisited
concepts specifically, not toward whichever domain has actually been
neglected the longest.

**Decision:** new `recommend_domain()` in `mistakes/service.py`,
completely independent of the ratio math: groups all mistakes by domain,
takes each domain's single *most recent* mistake timestamp (not its
oldest — a domain with one stale concept and one freshly-touched concept
is still an active domain), and returns whichever domain's most-recent
timestamp is furthest in the past. `create_session`'s automatic-mode
branch now calls `recommend_review(domain=recommend_domain())` instead of
`recommend_review()` unfiltered — domain chosen first, then that domain's
own top concept per #32's ranking. Returns `None` (not an error) when
there's no mistake data at all yet, same contract shape as
`recommend_review`.

**Status:** Decided (2026-08-13) — 139 tests pass (3 new in
`test_mistakes_service.py`: picks the staler of two domains; correctly
uses each domain's most-recent entry rather than its oldest; returns
`None` on no data — plus 1 in `test_sessions_service.py` proving the
actual planner-level behavior change: a domain whose top concept has a
*lower* raw overdue ratio still wins automatic mode when its domain has
gone untouched far longer than the higher-ratio domain). Verified against
the real `mistakes.db`: `recommend_domain()` picks `languages` (one
entry, aging quietly since 2026-08-11) over `english` (actively reviewed
as recently as today) — the exact fairness outcome this was built for.
Scheduling logic, not a live-model-behavior claim, so no real-conversation
recheck needed.

---

## 34. Rank `related_notes` by link type, not alphabetically

**Context:** Third item off `backlog.md`. `VaultIndex.related()`
returned the union of outgoing links and backlinks as one flat
alphabetically-sorted list, with no notion of which neighbor actually
mattered more — `create_session`'s fallback path (still the only concept
source for every non-language domain) takes the first `max_concepts - 1`
of whatever that list returns, so alphabetical accident directly decided
what got quizzed on. Surfaced concretely discussing a real "start a
session on TCP" scenario: `related_notes("TCP")` returns **20** notes on
the real vault (TCP is a hub, not a leaf) — `create_session` would have
anchored on `FTP` and `Linux Networking` (alphabetically first) over
`Handshake`/`UDP` (TCP's own direct, author-curated links), which are
obviously more central to actually understanding TCP.

**Decision:** `related()` now ranks in three tiers, using graph structure
already present, no new tracking: **mutual** links (in both the note's
outgoing links and its backlinks) first — the strongest real signal of
conceptual coupling; **outgoing-only** next — the note's own author
deliberately linked out to it; **incoming-only** last — something else
mentions this note, which for a well-connected hub can mean a broad
index-style note linking to dozens of unrelated things, not a sign of
real relevance to *this* note. Alphabetical within each tier for
determinism.

**Status:** Decided (2026-08-13) — 141 tests pass (2 new in
`test_retrieval_index.py`: tier ordering with a synthetic mutual/
outgoing-only/incoming-only graph; alphabetical-within-tier). Verified
against the real vault: `related_notes("TCP")` now returns `Handshake`,
`packet switching`, `TCP-IP`, `UDP` (TCP's real, direct associations)
ahead of `FTP`/`Linux Networking`, which is the actual behavioral change
this was built for. Pure ranking logic, no live-model-behavior claim, so
no real-conversation recheck needed.

**Separate bug found during validation, not fixed here, logged instead:**
`create_session("TCP")` anchors on `TCP-IP`, not `TCP` — `search()`'s
`EXACT_TITLE_BONUS` check is `query_lower in title.lower()`, a substring
test, so "TCP" gets the *same* full exact-match bonus against "TCP-IP" as
against "TCP" itself, and "TCP-IP" then wins on body-token tiebreaks.
Orthogonal to `related()`'s ranking (this is in `search()`, over anchor
*selection*, not neighbor ranking within an already-chosen anchor) — not
in scope for this fix. Added to `backlog.md`.

---

## 35. Rule 5: grounding applies to mid-conversation concepts too, not just the planned list

**Context:** Discussing a real "start a session on TCP" scenario
surfaced that rule 5's wording — "ground... before quizzing on a
concept" — never actually said whether that covers a concept the learner
raises spontaneously (e.g., bringing up UDP mid-TCP-session) or only the
concepts baked into `plan.concepts` at session start. In practice this
mostly already worked, since `search_notes`/`get_note`/`related_notes`
are live tools available every turn, not gated to planning time — but the
rule's *text* left it to interpretation. Given rules 1/10/11 all turned
out to have real gaps traced to exactly this kind of unstated scope, this
one was closed proactively rather than waiting for a transcript to expose
it.

**Decision:** rule 5 now states explicitly that grounding applies to any
concept about to be quizzed on, planned or not — a mid-conversation
detour into a related idea needs the same `search_notes`/`get_note`/
`related_notes` grounding as anything on today's list, not an implicit
exemption for being unplanned. Doesn't touch rule 5's existing vocabulary
carve-out (#30) — vocabulary distinctions still don't require grounding
regardless of when they come up; this clause is only about conceptual/
domain content raised outside the original plan.

**Status:** Proposed (2026-08-13) — 141 tests pass (wiring-level only).
Needs a real session: bring up a related-but-unplanned concept
mid-conversation and confirm, via `--debug`/the session log, that the
model actually calls the grounding tools for it before quizzing, rather
than answering from general knowledge just because it wasn't on the
original list.

---

## 36. Replace naive keyword scoring in `search_notes` with BM25

**Context:** Before patching the known substring-vs-equality bug in
`EXACT_TITLE_BONUS` (found validating #34), took a wider look at whether
`search()`'s scoring was improvable rather than just fixing the one bug.
It was — real numbers, not just theory: `TCP.md` (846 chars, "tcp" ×3)
scored *below* `TCP-IP.md` (4171 chars, "tcp" ×9) even discounting the
bonus bug, because raw body-token counts have zero length normalization —
a long, broad note systematically outranks a short, precise one. Also
confirmed no IDF: searching "transport layer" let `TCP-IP` creep into
rank #2 partly because "layer" is common across 60 of 1520 notes and
scored the same per-occurrence as a rare, distinctive term.

**Decision:** replaced the naive weighted-count scorer with BM25 computed
independently per field (title, body — not full BM25F's combined
cross-field pseudo-frequency, a deliberate simplification), combined with
the existing field-importance weights (`TITLE_WEIGHT`/`BODY_WEIGHT`/
`TAG_WEIGHT` unchanged in value — they're relative-importance ratios
between fields, not scale-dependent, so they carry over). Standard
textbook BM25 parameters (`k1=1.5`, `b=0.75`), not vault-tuned —
deliberately adopting a real, well-understood formula instead of more
hand-picked magic numbers. `EXACT_TITLE_BONUS` now requires true title
equality, not `query in title` substring containment (the originally
found bug) — kept as a small additional signal on top of BM25 rather than
removed, since BM25's own title-field scoring already favors short,
closely-matching titles fairly strongly on its own once length
normalization is correct.

**Why per-field BM25 instead of full BM25F:** full BM25F combines
per-field term frequencies into one pseudo-frequency before applying a
single IDF; independent per-field BM25 (each field with its own IDF and
length normalization) is simpler to reason about, test, and tune, at the
cost of not being the textbook-exact multi-field formula. A defensible,
documented simplification, not an accidental one.

**Considered and deferred, not rejected: embeddings/semantic search.**
Already named as future work in #12. BM25 fixes the two concretely
identified problems (length normalization, IDF) without a new dependency
or ongoing embedding cost; embeddings would additionally solve
different-wording-same-meaning queries that no lexical scorer can (a
query using none of a note's actual words), which BM25 does not and
cannot fix — a genuinely separate capability, not a strictly-better
version of the same thing, and a bigger standalone decision than this one
warranted.

**Status:** Decided (2026-08-13) — 144 tests pass (3 new: exact-equality
beats substring-title match; length normalization favors a short focused
note over a long diluted one with more raw occurrences; IDF favors a rare
term over a common one at equal term-frequency/length). Verified against
the real vault: `search("TCP")` now ranks `TCP` above `TCP-IP` (the
original bug); `search("transport layer")` no longer surfaces `TCP-IP` in
the top 5 at all (previously rank #2); `create_session("TCP")` now
correctly anchors on `TCP` itself and produces
`['TCP', 'Handshake', 'packet switching', 'TCP-IP', 'UDP']` — the exact
sensible neighborhood from the original TCP discussion, combining this
fix with #34's tiered `related()` ranking. Pure ranking/retrieval logic,
no live-model-behavior claim, so no real-conversation recheck needed.

---

## 37. Weighted-graph centrality: in-degree as a foundational-ness signal, first application (blind-spot cold start)

**Context:** User's idea from earlier in this session, logged in
`backlog.md`: the more a vault note is pointed at, the more foundational
it likely is — naive in-degree centrality. Flagged at the time as needing
its own scoping discussion (where it plugs in, how normalized) before
building, since several applications were named without picking one.

**Decision — the core primitive:** `VaultIndex.most_important(limit)` in
`retrieval/index.py`, ranking notes by backlink count descending. Pure
aggregation over `_backlinks`, already built at index time — no new
indexing pass, matching the original idea's own observation that this is
cheap. Deliberately backlinks only, not outgoing links too: the actual
claim is about being pointed at, not about how much a note itself
references elsewhere. Exposed via `retrieval/service.py`'s
`most_important_notes` and exported from `learning_os.retrieval`,
matching the existing `search_notes`/`get_note`/`related_notes` pattern.

**Decision — first application, picked over the other three named
in `backlog.md`:** a cold-start fallback for `create_session`'s automatic
mode. Previously, zero mistakes tracked anywhere meant an immediate
`ValueError` ("name a topic explicitly") — a real dead end for a fresh
install or a completely untouched domain. `_find_blind_spot_topic`
(`sessions/service.py`) now scans the top 20 most-important vault notes
for the first one with zero entries in `get_learning_profile()` (i.e.
never tracked as a mistake, in any domain) and offers that instead,
before falling through to the existing error. Objective phrasing
distinguishes this from a real "due for review" pick: "Explore {topic} —
a foundational concept not yet reviewed." The other three applications
named in `backlog.md` (tiebreak within `related()`'s tiers; a priority
layer on top of #32/#33 for competing overdue concepts; weighting
Career/CV strength toward hub concepts) remain unbuilt, left in
`backlog.md` — this primitive supports all of them without committing to
which comes next.

**Real, non-obvious finding while testing:** `_find_blind_spot_topic`'s
own "all candidates already tracked" branch turns out to be
mathematically unreachable through `create_session` — `recommend_domain`/
`recommend_review` only return empty when the *entire* mistakes table is
empty, which is exactly the one condition under which
`_find_blind_spot_topic` gets called at all, so `get_learning_profile()`
inside it is always querying an empty table in that calling context. The
branch is still correct, real behavior of the helper in isolation (worth
keeping — it's not called only from here, and its own contract should be
correct regardless of caller), but had to be tested by importing
`_find_blind_spot_topic` directly rather than through `create_session`,
since the integration path can never actually reach it.

**Status:** Decided (2026-08-13) — 149 tests pass (6 new: `most_important`
ranks by backlink count / respects limit / handles an empty vault;
`create_session` falls back to the blind-spot pick with the right
objective wording when nothing's tracked; `_find_blind_spot_topic`
returns `None` directly when all candidates are already tracked). Verified
against the real vault: top-10 most-important notes are genuinely
foundational hub concepts across multiple domains (`HTTP`,
`Machine Learning`, `operating system`, `Big O notation`, `kernel`,
`router`, `Chemical Reaction`, `NLP`, ...), not noise; `_find_blind_spot_topic()`
called directly against the real `mistakes.db` correctly picks `HTTP` —
the most-important real note that happens to have zero tracked mistakes
today. The known raw-in-degree tradeoff from the original backlog note
(conflating "foundational" with "generic and overused") still applies and
is unresolved — PageRank-style recursive weighting remains the named fix
if that proves to matter in practice, same as before.

---

## 38. Importance-based tiebreak within `related()`'s tiers

**Context:** Second application of #37's centrality primitive, and the
first of the three `backlog.md` named as still open after #37. `related()`
already ranks into three tiers (mutual/outgoing-only/incoming-only, #34),
but fell back to plain alphabetical order within each — for a
well-connected hub note with many same-tier neighbors, the neighbor
surfaced first was arbitrary rather than the one actually most central to
the vault.

**Decision:** added `VaultIndex._importance(key)`, a thin wrapper around
the backlink-count expression `most_important` already computed inline —
shared now across 4 call sites (3 in `related()`, 1 in `most_important`,
refactored to use it too) so the two rankings can't silently drift apart.
`related()`'s three tier sorts now use `(-importance, key)` as their sort
key — same tuple idiom `most_important` already used — instead of plain
alphabetical. Tier order itself is unchanged, only the ordering within
each tier.

**Status:** Decided (2026-08-13) — planned in plan mode (2 Explore/Plan
subagent passes confirming exact current code and tracing test impact
before writing anything), then implemented exactly as planned. 150 tests
pass (1 new: two same-tier candidates where the alphabetically-later one
has strictly more backlinks now correctly ranks first — a real behavior
change no prior test could have caught). Verified against the real vault:
`related("TCP")`'s mutual tier flips from `Handshake, packet switching,
TCP-IP, UDP` to `TCP-IP, Handshake, UDP, packet switching`, matching a
hand-computed expected order exactly; `most_important(limit=10)`'s output
confirmed unchanged after the `_importance` refactor (pure dedup, no
behavior change there). Pure ranking logic, no live-model-behavior claim,
so no real-conversation recheck needed.

---

## 39. Priority layer: vault importance as a tiebreak on top of spaced-repetition urgency

**Context:** Last-but-one remaining application of the centrality
primitive (#37/#38) named in `backlog.md`: "a priority signal layered on
top of #32/#33 for which concept within an already-overdue domain is
most worth consolidating first." Planned in plan mode, with two
Explore/Plan subagent passes confirming exact current code before writing
anything, since this one touched a genuine architectural fork.

**Architecture decision:** `recommend_review` is one of the 18 registered
model-facing tools (`tools.md`) — the model can call it directly
mid-conversation. Blending importance into it directly would mean
`mistakes/service.py` importing `learning_os.retrieval` (confirmed no
circular-import risk either direction, but `architecture.md` frames these
as deliberately separate, swappable modules) and would silently change a
documented tool's live behavior with no stated expectation of it.
Decided: keep `recommend_review`'s contract and output byte-for-byte
unchanged. Added `recommend_review_scored` (`mistakes/service.py`) — same
ranking, with each concept's raw `_overdue_ratio` attached — and made
`recommend_review` a thin wrapper over it. The actual importance-blending
(`_prioritize_by_importance`, new `OVERDUE_TIE_BUCKET_SIZE` constant) lives
in `sessions/service.py`, consistent with where `_language_concepts`
(#31) and `_find_blind_spot_topic` (#37) already do cross-cutting planner
logic rather than reaching into the lower modules. New
`VaultIndex.importance(title)`/`concept_importance` (public single-note
counterpart to `most_important`) returns 0 for a concept that isn't a
real vault note title, rather than erroring — handles the real, common
case (6 of 10 tracked concepts today are freeform language-mistake
descriptions, not vault titles) with no special-casing needed by callers.

**Decision — the tiebreak mechanism:** concepts whose `_overdue_ratio`
rounds to the same `OVERDUE_TIE_BUCKET_SIZE=0.25`-wide bucket are
re-ranked by backlink count; Python's stable sort keeps
`recommend_review_scored`'s own urgency/understanding order as the
tiebreak beneath that. A genuine urgency gap (different bucket) is never
overridden by importance, regardless of how foundational either concept
is. `0.25` is a naive-v1 constant in the same spirit as
`MIN`/`MAX_REVIEW_INTERVAL_DAYS`/`BM25_K1` elsewhere — not tuned against
real data, a defensible starting point.

**Real-data limit, confirmed directly, stated plainly rather than
implied away:** the only domain with 2+ tracked concepts today
(`classical-ml`: `Adam optimizer` ratio 1.047, `Optimizer` ratio 0.166 —
0.88 apart, several buckets under the scheme above, and tied on
importance at 2 backlinks each regardless) does not exercise this
feature. Re-running the full real pipeline confirms
`_prioritize_by_importance` is a no-op on both real domains checked
(`languages` has one concept; `classical-ml`'s gap is genuine, not close)
— `create_session(topic=None)`'s pick is unchanged today. This is an
honest data-shape fact, not a bug: no pair of concepts in the current
`mistakes.db` both share an overdue bucket and differ in importance.

**Status:** Decided (2026-08-13) — 161 tests pass (11 new: `recommend_review_scored`
parity with `recommend_review` plus empty-case; `importance()`'s three
cases in `retrieval/index.py`; four `_prioritize_by_importance`/
`create_session` tests proving the actual behavior change synthetically
— same-bucket concepts re-ranked by importance, a genuine urgency gap
never overridden, unresolved concepts get importance 0 and keep relative
order, and an end-to-end `create_session` case with synthetic timestamps
mirroring #32/#33's own validation pattern; two real-vault
`concept_importance` checks). Verified against the real vault/DB as
described above. Live-model-behavior claim only insofar as
`recommend_review`'s tool contract was checked to be unchanged (confirmed
by the existing test suite passing unmodified) — the new
`_prioritize_by_importance` logic is pure backend ranking, not a prompt
change, so no real-conversation recheck is needed.

---

## 40. Career/CV summary weighted toward demonstrated mastery of hub concepts

**Context:** Last remaining application of the centrality primitive named
in `backlog.md`. `summarize_skills_for_cv` sent every qualifying strength
to the LLM with no notion of which was more foundational — a demonstrated
strength in something central to the vault (e.g. `Optimizer`) read no
differently from one in something peripheral.

**Scoping decision:** applied to `summarize_skills_for_cv` only, not
`analyze_job_fit`, despite both being registered Career tools
(`tools.md`). Job-fit matching should reflect relevance to *that specific
job*, not general vault centrality — a job can genuinely need a niche
skill that isn't foundational to this vault at all, so blending
vault-wide importance into job matching would be the wrong signal there.
Confirmed by a new regression test that `analyze_job_fit`'s prompt
contains no `vault_importance` field.

**Decision:** `career/service.py`'s `summarize_skills_for_cv` computes
`concept_importance` (#39's primitive) per qualifying strength, sorts
strengths by it descending, and passes an importance dict through to
`career/prompt.py`'s `build_cv_summary_prompt`/`_format_profile`, which
now render a `vault_importance=N` field per line and instruct the model
to lead with and emphasize higher-importance concepts within each domain
— explicitly *not* to drop a genuine niche strength for having low
importance, only to not lead with it. Concepts that aren't real vault
note titles get importance 0 and simply sort last, no special-casing
needed (same handling as #39). `_format_profile`'s `importance` parameter
is optional and defaults to omitting the field entirely, so
`build_job_fit_prompt`'s call site is untouched.

**Status:** Decided for the data-plumbing/prompt-construction logic
(163 tests pass, 2 new: importance-sort actually reorders — inserted
importance-ascending, asserted importance-descending in the prompt text
— and the `analyze_job_fit` regression guard). Verified against the real
DB/vault: only one real strength currently qualifies (`Optimizer`,
understanding 0.85, importance 2), so — same honest limitation as #39 —
there's nothing to visibly reorder today, but the prompt construction was
confirmed correct against real data end-to-end. **Proposed**, not fully
Decided, for the actual claim that matters: whether the LLM's summary
genuinely leads with foundational concepts when several real strengths
exist. That's a live-model-behavior claim (a prompt-template change) and
needs a real `summarize_skills_for_cv()` call once enough tracked
strengths exist to make the ordering visible — added to `backlog.md`'s
pending-validation list, same bar as the tutoring prompt rules.

---

## 41. Rule 5 gap found live: the session's own anchor concept opened ungrounded

**Context:** A real `learning-os-chat --debug` transcript (topic "TCP",
2026-08-13) showed the session's only tool call before the opening
question was `get_recent_mistakes` (rule 7) — no `search_notes`/`get_note`
call for "TCP" itself, which was both the session's anchor concept
(`plan.concepts[0]`) and the very thing the opening question ("how would
you explain TCP in your own words?") quizzed on. The direct explanation
given two turns later, after the learner signaled "I don't know" twice
(rule 1), was also delivered with no grounding call preceding it.
`search_notes("TCP")` was first invoked several turns after that, only
because the learner explicitly asked for related concepts — at which
point it returned a real, substantive vault note ("**TCP** (Transmission
Control Protocol) is a connection-oriented transport-layer protocol...")
that had been sitting there ungrounded the whole time.

This is a different gap from the two already tracked: not #35 (grounding
*unplanned* mid-conversation concepts — this was the *planned* one, the
thing the whole session is built around), and not rule 10 (which only
fires when a lookup comes back *empty* — here no lookup was attempted at
all, so no disclosure fired and the letter of rule 10 was technically
satisfied while the explanation was, in effect, silently sourced from the
model's own training knowledge with the same confident tone a grounded
answer would carry).

Likely contributing cause: rule 8 ("open the session yourself... don't
wait for the learner to start") gave no instruction to ground before that
opening question, leaving "open immediately" and "ground first" in
apparent tension; the model picked speed.

**Decision:** strengthened rule 5 (`conversation/prompt.py`) with an
explicit clause: grounding the anchor concept applies to the *opening*
question too, not only to concepts raised later — call
`search_notes`/`get_note` on the session's own anchor concept before
asking anything, even the first question. Rule 8 now cross-references
rule 5 directly ("Ground the anchor concept per rule 5 first; do this
before your greeting, not after") instead of staying silent on the
ordering.

**Status:** Decided (2026-08-15) — **confirmed live**, the same bar #25's
rule 10 was held to. Two fresh `--debug` runs on vault-anchored topics,
each exercising only the opening turn (that is the entire claim):

- `TCP` (the topic that originally failed): tool call **#1** is
  `search_notes("TCP")`, returning the real vault note, followed by
  `get_recent_mistakes` (rule 7), and only then the opening question
  "How would you explain TCP in your own words?" — the exact ordering
  that was inverted before.
- `Gradient descent` (a topic with tracked mistake history, so rule 7 has
  something to find): identical pattern — `search_notes` first,
  `get_recent_mistakes` second, opening question last.

Proposed on 2026-08-13 and confirmed on 2026-08-15; the offline suite
never could have caught this, since it asserts wiring rather than live
model behavior.

**Observed during validation, unrelated to this rule:** `create_session("TCP")`
infers `domain='general'`, because the vault's TCP note carries neither a
frontmatter `domain:` nor any tags, so `_infer_domain` falls through to
its default. Mistakes saved in that session would be filed under
`general` rather than anything networking-shaped, which quietly weakens
`recommend_domain`'s (#33) per-domain rotation. Logged in `backlog.md`.

---

## 42. `--debug` renders full tool calls, as one shared module for both loops

**Context:** #41 was found by reading a real `--debug` transcript, and
nearly wasn't: both loops printed each tool call as a single line
truncated at 200 chars (`f"\n[tool call] {name}({args}) -> {content[:200]}"`),
duplicated in `conversation/loop.py` and `realtime/loop.py`. That format
is adequate for "did a call happen" but not for the questions
`backlog.md`'s pending-validation list actually asks — *which* concept
was grounded, *when* relative to the opening question, and whether the
result came back substantive or empty. A `search_notes` result is
comfortably past 200 chars, so exactly the part that decides the question
(the returned note content) is the part that got cut. Counting calls by
hand across an interleaved transcript to establish ordering was the other
half of the problem.

**Decision:** a single `learning_os/debug_output.py` with
`print_tool_call(number, name, arguments, result_json)`, imported by both
loops. Divider-delimited block per call, sequence number in the header,
arguments and result both pretty-printed as indented JSON, nothing
truncated. Placed at the package root rather than inside either loop's
package: it is shared presentation used by two sibling consumers, and
`architecture.md`'s "backend owns the logic" split makes tool-call
rendering a backend concern, not something either transport re-implements
for itself. The text loop threads an `itertools.count` through
`ConversationState` so numbering is continuous across a whole session
rather than restarting each turn; the voice loop keeps a local counter
since its session is one long-lived coroutine.

Debug-only presentation, so this deliberately gets no test of its own —
the offline suite asserts on behavior, and asserting on print formatting
would just pin the string.

**Status:** Decided (2026-08-13) — 163 tests pass. Not a
live-model-behavior claim; it is the instrument the remaining
live-behavior claims (#41 especially) get checked with.

---

## 43. Session difficulty/duration from tracked evidence, in evidence-scoped vocabulary

**Context:** `backlog.md`'s session-planner item. `target_difficulty` is
hardcoded `DEFAULT_TARGET_DIFFICULTY = "beginner"` and
`expected_duration_minutes` is `max(15, 5 × concept_count)` — both flagged
provisional in Milestone 4 "until Milestone 6 gives mastery data to inform
them for real". Milestone 6 shipped that data; the planner never came back
for it.

Scoping it surfaced the reason the item is worth doing at all, and it
isn't the arithmetic: **neither field has a reader.** They are written in
`create_session`, declared on `SessionPlan`, and consumed by nothing —
`build_system_prompt` interpolates `domain`, `objective`, and `concepts`
only, and `tools.md` doesn't mention either field. Deriving better values
without wiring them into the prompt would be a no-op with tests attached.
So the change is two halves, and the second carries the value.

Two properties of the mistake store constrain the mapping:

- `DEFAULT_CONCEPTUAL_UNDERSTANDING = 1.0` means a never-tracked concept
  scores a *perfect* 1.0. Averaging `estimate_mastery` over a plan's
  concepts would therefore rate every fresh session as maximally
  understood, and would invert the blind-spot cold-start path (#37), whose
  entire purpose is picking a foundational concept with *no* tracked
  history. "Untracked" has to be its own state, not a high score.
- The store records only failures. `mistake_count` counts mistakes, and
  `MistakeEntry.corrected` never flips to `True`, so nothing anywhere
  records a concept being handled *correctly*. High understanding can only
  ever mean "old, few, low-confidence mistakes" — never demonstrated
  success. Evidence is one-sided, and the label has to stay inside what
  that supports.

**Decision:**

1. **Evidence classes, not an averaged scalar.** One
   `get_learning_profile(domain)` call classifies each planned concept as
   `untracked` (absent from the profile), `shaky`, or `settled` (split on
   `conceptual_understanding`). `target_difficulty` derives from the
   *tracked* concepts only; with none tracked it keeps today's default,
   which is the honest answer when there is no evidence either way. Ties
   lean toward the deeper start, per `pedagogy.md`'s desirable-difficulty
   point — smooth sessions are the failure mode, not the goal.
2. **Depth-scoped vocabulary** (`foundational` / `consolidating` /
   `extending`) replaces `beginner`/`intermediate`/`advanced`.
   `pedagogy.md`'s "Realistic goals" section requires every mastery/level
   signal to be scoped to conceptual understanding and to not imply
   overall competence; "advanced" reads as a competence claim, and given
   the failures-only store there is no data behind it. The field now names
   *where to start the questioning*, which is a claim the data can carry.
3. **Duration stays out of the prompt.** Mastery data sizes it honestly
   (shaky concepts cost more minutes than settled ones, 15-minute floor
   kept), and it remains a planning/telemetry value. Putting a minute
   budget in front of the model invites clock-watching, which pulls
   directly against rule 2 (resolve the current claim before moving on)
   and rule 11 (applicative follow-up before a concept counts as covered)
   — the two rules most recently strengthened, and the ones a rushed
   session drops first.
4. **Prompt wiring states where to start, not a level to announce**:
   foundational opens from mechanism and definitions; extending skips the
   definition and opens with a rule-11 applicative scenario. Both loops
   share `build_system_prompt`, so voice inherits this with no separate
   change — though note voice sessions can't persist mistakes (#22), so
   voice consumes this evidence without ever generating any.

**Explicit non-goal:** per-concept evidence annotations in the prompt
(`TCP (3 mistakes tracked)`, `Handshake (no history)`). Probably where the
real value sits, since a single session-level label flattens a plan whose
concepts genuinely differ — but it needs a new `SessionPlan` field and a
`domain-model.md` change, which is a separate decision from the one this
entry closes. Named here so it doesn't get silently absorbed.

**Status:** Proposed (2026-08-15) — scoped, not yet built. Thresholds will
be v1 constants stated with their reasoning rather than tuned: today's
store holds 10 tracked (domain, concept) pairs, 8 of them with a single
mistake, understanding spanning 0.02–0.85 — enough to sanity-check a
mapping against (`Gradient descent` at 0.03 must come out foundational),
nowhere near enough to fit a threshold to, the same position
`OVERDUE_TIE_BUCKET_SIZE` was in.

---

## 44. Evidence memory: two-sided evidence, and an honest comparison against Anki

**Context:** Stated goal (2026-08-15): emulate Anki's spaced repetition as
closely as is sensible, and beat it where this system structurally can.
This entry exists because the immediate question — should untracked
concepts default to 0 instead of 1.0 (#43) — turns out to be unanswerable
inside the current model, and the reason why is the design question worth
settling.

Today the store is one-sided: `save_mistake` writes a row when something
goes wrong, nothing is written when something goes right, and
`MistakeEntry.corrected` never flips to `True`. Understanding is
`1.0 - average(confidence of recorded mistakes)`, and the interval is that
number mapped linearly onto 1–14 days (#32).

With one-sided evidence, **no default for "never tested" is honest**:

- `1.0` (today) makes an untested concept look perfectly mastered — it is
  the empty-sum identity of a failure metric, not a claim, but every
  consumer has to remember to check `mistake_count` to know that.
- `0.0` inverts the absurdity instead of fixing it: a concept you failed
  once scores `1 - 0.4 = 0.6`, so "never seen" would rank *below*
  "demonstrably failed", and — since successes are never recorded — it
  could never rise. A concept you know well but never got wrong would sit
  at 0 permanently.

One scalar is carrying two independent facts: how much evidence exists,
and what that evidence says. That is the actual defect.

**What Anki actually does** (stated so the comparison is real):
its current default scheduler, FSRS, models memory as difficulty,
stability, and retrievability, and schedules a card for the moment
predicted recall decays to a target retention (0.9 by default), with
parameters optimized from the user's own review log. SM-2, its
predecessor and still the legacy option, multiplies a card's interval by
a per-card ease factor and collapses it on a lapse. Both take a
**self-reported** grade (Again/Hard/Good/Easy) on an atomic item, and both
depend on that grade arriving on every single review. Exact FSRS
parameter/version details should be re-checked against Anki's own docs
before any implementation — the design below deliberately doesn't depend
on them.

**Where this system differs structurally** — the part that decides whether
copying Anki is even the right target:

- *Advantage — observation quality.* Anki's grade is self-reported after
  the answer is revealed, which is exactly the condition under which
  hindsight bias inflates self-assessment. Here the grade comes from an
  explanation the learner produced *before* seeing any answer (rules 1, 2,
  11). That is a better observation, not just a different one.
- *Advantage — what an item can test.* A card tests recall of one fixed
  face. A conversation can test explanation in the learner's own words and
  transfer to a novel scenario (rule 11), which is the thing `pedagogy.md`
  says separates real understanding from recited fluency.
- *Advantage — typed misconceptions.* `MistakeEntry` records category and
  explanation, so a failure says *how* it failed. Anki knows only that a
  card lapsed. Re-quizzing can target the specific error rather than
  repeating the same prompt.
- *Advantage — no authoring cost.* The vault is the deck; BM25 search and
  `related_notes` build items, so nothing has to be hand-written into
  cards first.
- *Decisive disadvantage — throughput.* Twenty minutes of Anki yields on
  the order of 100–200 graded observations. Twenty minutes of conversation
  yields roughly five. That is a two-order-of-magnitude gap in the input
  any scheduling algorithm eats, and it is why this design must not copy
  FSRS's fitted-parameter approach: fitting needs something like 10^3
  observations, and this system will have 10^1 for a long time (today: 10
  tracked pairs, 8 of them a single mistake).
- *Disadvantage — capture reliability.* Anki cannot miss a review. Here
  capture depends on the model calling a tool mid-conversation, which
  rule 3 already fights for and which does not work at all in voice (#22).

**Proposed decision** (design only — no code, see Status):

1. **A two-sided `evidence` table**, not a rewrite of `mistakes`:
   `(domain, concept, timestamp, outcome, quality, source, session_id)`.
   Existing mistake rows stay exactly where they are and are read as
   negative evidence, so the export/backup trail stays intact and nothing
   already recorded is destructively migrated. (Amended 2026-08-15: as
   first written this sentence claimed #10's git-tracked export as an
   existing safeguard. It wasn't — #10 was decided and never built. It
   exists now, as #46; the claim was made true rather than left standing
   as an assumption.)
2. **Capture at end of session, in one judged pass — not per turn.**
   Asking the model to call a `save_success` tool on every correct answer
   doubles the burden rule 3 already struggles to enforce. Instead,
   `finish_session` grades each planned concept once from the transcript:
   `not_reached / incorrect / partial / correct / correct_with_application`
   (the last being rule 11's transfer question actually cleared). This
   follows the career module's precedent (#19): use an LLM where the task
   is genuinely semantic, unlike `summarize_session`'s deliberate
   substring naivety.
   **Side effect worth naming: this would also fix #22.** Voice sessions
   can't call `save_mistake` reliably, but their transcripts are already
   logged — a transcript-graded pass captures voice evidence without
   depending on in-conversation tool calls at all. The documented voice
   limitation stops being structural.
3. **Anki-shaped per-concept state with fixed, documented constants**:
   stability (in days) and difficulty, updated multiplicatively per
   observation — success extends stability, failure cuts it — scheduled on
   FSRS's *semantics* (review when predicted recall reaches a target
   retention) but never with per-user parameter fitting, per the
   throughput argument above.
4. **`_overdue_ratio` keeps its exact shape** (elapsed ÷ interval, >1 means
   overdue). This replaces *how the interval is computed*, not the
   scheduling interface, so `recommend_review_scored`, `recommend_domain`
   (#33), the importance tiebreak (#39) and the session planner keep
   working untouched.
5. **"No evidence" stays representable as absence**, never as 0 or 1 —
   #43's small fix becomes standing policy: the scalar reports what
   evidence says, and absence of evidence is reported as absence.
6. **`corrected` finally gets meaning**: a later `correct` observation
   marks that concept's earlier mistakes corrected, closing a
   carried-forward known gap.

**What this explicitly does not claim.** Not that it beats Anki on
retention. `pedagogy.md`'s honest position stands: this system's case is
lower-friction habit formation and coverage of open-ended material, not
proven retention per unit time. Better-quality observations that are 100×
sparser are not automatically a better scheduler, and for atomic factual
recall (vocabulary, formulas, dates) Anki should be expected to stay
ahead. The defensible split is: Anki for atomic facts, this system for
explanation and transfer. Every signal here remains scoped to conceptual
understanding, not competence (`pedagogy.md`, "Realistic goals").

**Status:** Proposed (2026-08-15) — design only, nothing built, no code
written. Deliberately staged behind three prerequisites: (a) #43's
"no evidence" fix, which is small and independent; (b) enough real
sessions for a two-sided store to have anything to hold — the binding
constraint is data volume, not algorithm quality, and building a
sophisticated scheduler over 10 observations optimizes the wrong end;
(c) a new `pedagogy.md` section covering this Anki comparison, since
CLAUDE.md gates any new learning mechanism on that doc rather than on
the mechanism sounding reasonable. Open question not resolved here: what
to do with concepts that get discussed but never actually quizzed — they
generate no observation of either sign, and treating discussion as
evidence would reintroduce exactly the fluency-as-understanding error
`pedagogy.md` warns about.

---

## 45. `estimate_mastery` reports absence of evidence as absence, not as a score

**Context:** Scoping #43 turned up that `DEFAULT_CONCEPTUAL_UNDERSTANDING
= 1.0` makes a never-tracked concept score as perfectly understood. The
question raised in review — why not default to 0.0 instead — is answered
in #44: with a failures-only store, neither number is honest. 1.0 makes
ignorance look like mastery; 0.0 would rank a never-seen concept *below*
one that was demonstrably failed (a single failed concept scores
`1 - 0.4 = 0.6`), and could never rise, because successes are not
recorded anywhere.

Tracing the call sites narrowed the blast radius well below what the
constant's prominence suggests. `_conceptual_understanding` has four
callers, and three of them — `_overdue_ratio`, `get_learning_profile`,
`recommend_review_scored` — compute from mistakes already grouped by
concept, so their input is never empty and the default cannot fire.
Every `MasteryEstimate` in a profile therefore has `mistake_count >= 1`.
Exactly one path could return the invented value: `estimate_mastery`.

Its reach is also narrower than first stated: `estimate_mastery` is *not*
in `TUTORING_TOOLS`, so the in-session tutor (text or voice) cannot call
it. It reaches callers through the tool registry — the MCP server's 18
tools (#24), so a Claude Desktop/Code client asking "how well do I know
X?" about anything untracked was the real exposure.

**Decision:** `estimate_mastery` returns `float | None`, with `None` for a
concept that has no recorded mistakes, documented in its docstring, in the
registry description the model actually reads, and in `tools.md`.
`DEFAULT_CONCEPTUAL_UNDERSTANDING` is deleted rather than left unused, and
`_conceptual_understanding` now raises on an empty list instead of
silently inventing a value — the three internal callers cannot hit it, and
the raise is what keeps that property from quietly eroding. This is #44's
policy point 5 landing early, since it is small and independent of the
rest of that proposal.

**Deliberately not fixed here, and worth naming:** the whole metric rests
on `confidence`, a field no one defines for the model. It is absent from
the tutoring prompt (rule 3 specifies `domain` and `concept` only), from
the registry description, from `tools.md`, and from `domain-model.md`,
which lists the field name and nothing more. So the model invents the
number on every correction, and the formula then reads it as "how much the
learner does *not* understand" when the name says "how sure the tutor is
that this was a mistake" — the observer's certainty and the learner's
deficit are different quantities. Meanwhile `severity`, which is the field
that would carry magnitude, is written on every row and read by no
calculation at all. Defining these belongs with #44, where what counts as
an observation has to be pinned down anyway; fixing it here would change
what every existing row means without a migration story.

**Status:** Decided (2026-08-15) — 164 tests pass, one rewritten (the old
test pinned the 1.0 default) and one added, asserting that absence and a
worst-possible score are distinguishable rather than both reading as a
number. Verified against the real `mistakes.db`: `Gradient descent`
(math-foundations) still returns 0.03 and `Optimizer` 0.85, while an
untracked `TCP` now returns `None` instead of 1.0, serializing to `null`
for MCP callers.

---

## 46. Building #10's backups and flat-file export, three months after deciding them

**Context:** #10 (2026-08-10) decided SQLite as the live store plus two
safeguards: periodic backups of the `.db`, and a git-tracked flat-file
export as a diffable audit trail. Neither was ever built — `grep -ril
export backend/src/` returned nothing. Surfaced while auditing what else
is broken, and it was the most serious thing on that list: `mistakes.db`
is the only artifact in this project git can't recover. The vault lives in
Obsidian, the code and docs live in git; the mistake history exists in
exactly one unversioned binary file. #44 then compounded it by citing the
audit trail as an existing safeguard for a future migration (that sentence
is now amended in place).

**Decision:** a `mistakes/archive.py` module, with the specifics chosen as
follows:

- **Paths derive from `db_path`, not from their own settings.** A
  redirected database — tests, a scratch copy, a second vault — must not
  be able to write into the real repo's export. Making `export_path()`
  and `backups_dir()` functions of `db_path` makes that structural rather
  than a rule to remember: the existing test suite redirects `DB_PATH`
  already, so every test got correct isolation for free.
- **JSON, not Markdown.** #10 left the format open ("Markdown/JSON"). JSON
  round-trips losslessly, so the export is simultaneously the audit trail
  and a recovery source — every field survives, which a prose rendering
  would not. Deterministically ordered (timestamp, domain, concept) and
  `sort_keys=True`, because an audit trail that reorders itself between
  writes produces diff noise instead of history.
- **Whole-file rewrite per write**, not append. At tens of rows the cost is
  nothing and the file is consistent with the database by construction.
- **`sqlite3`'s native backup API, not `shutil.copy`.** The live connection
  can be mid-write; only the native API guarantees a consistent snapshot.
- **Write-triggered but interval-gated** (`BACKUP_INTERVAL`, 1 day,
  `BACKUPS_TO_KEEP`, 10). No new data means no new backup. Since a
  write-triggered backup only fires when data changes — which is when a
  backup is least urgent — `learning-os-backup` exists as the entry point
  for a real periodic schedule (cron/systemd), which is what #10's word
  "periodic" actually requires.
- **Hooked at `store.insert_mistake`**, the single choke point every write
  path funnels through, rather than at `save_mistake` — so a future writer
  that bypasses the service layer is still covered.
- **Failures are swallowed and reported on stderr.** The row is already
  committed when the archive runs; losing the audit copy is bad, crashing
  a live tutoring session after the data is safely stored is worse. Silent
  failure would be worse still, hence the stderr line.

**Status:** Decided (2026-08-15) — 173 tests pass, 9 new, including the
two that matter most: a backup is reopened as a database and read back
(proving it's a real snapshot, not a file of plausible size), and a
forced export failure leaves the mistake committed while printing to
stderr. Verified for real: `uv run learning-os-backup` exported all 12
rows of the live `mistakes.db` to `data/mistakes_export.json` and produced
a working `data/backups/mistakes-20260815T201036Z.db`. `.gitignore`
already excluded `*.db` and `backups/`, so the export is tracked and the
binaries aren't, which is exactly #10's intended split.

**Note on what is now in git:** the export contains real mistake content
(concepts, explanations, timestamps) in a personal repo. That is what #10
asked for — a human-readable history — but it is worth being aware of
before this repo is ever shared or made public.

---

## 47. Text sessions write transcripts too, through the same log as voice

**Context:** Voice sessions have written `logs/<session_id>.log` since
Milestone 9 — transcript plus every tool call. Text sessions wrote
nothing: `--debug` printed to the terminal and the turns lived in the
in-memory `_SESSIONS` dict until the process exited. Reviewing a text
session therefore meant copying scrollback by hand before closing the
window, which is how #41's original evidence had to be gathered.

The asymmetry also blocks #44 directly: its end-of-session grading reads
the transcript, and half the sessions had no transcript to read.

**Decision:** `SessionLog` moves from `realtime/` to top-level
`learning_os/session_log.py` — two loops use it now, the same reasoning
that moved `llm_client` (#19) and placed `debug_output` (#42) at the root
— and `conversation/loop.py` writes through it at every point the voice
loop does: `SESSION START`, `USER:`, `ASSISTANT:`, `TOOL CALL:`,
`SUMMARY:`, `SESSION END`. The line format is deliberately identical, so
#44's grading can read both kinds of session with one parser rather than
two.

Tool calls are logged **regardless of `--debug`**: the flag is about what
the terminal shows while you sit there, not about whether the session
leaves a record. `ConversationState` carries the log as `SessionLog |
None`, so tests and library callers can drive the loop without opening
files.

**Test isolation, added with it:** an autouse `conftest.py` fixture points
`LOG_DIR` at a per-test `tmp_path`. Without it every test that starts a
conversation would write into the repo's real `logs/` — the same class of
problem #46 avoided by deriving its paths from `db_path`, fixed the same
way rather than left to discipline.

**Status:** Decided (2026-08-15) — 175 tests pass, 2 new (a full
start/send/end cycle produces a transcript containing the tool call, the
user turn, the summary and a terminating `SESSION END`; tool calls are
logged with `debug=False`). Verified for real: a live `TCP` session wrote
`logs/1aa66e04-….log` with all five planned concepts grounded via
`search_notes` before the opening question.

**Incidental third confirmation of #41, with useful variance:** in that
run the model called `get_recent_mistakes` *first* and then grounded all
five concepts, where the two runs recorded under #41 grounded the anchor
first and only the anchor. Rules 5 and 7 impose no order between
themselves, so all three orderings satisfy the rule — worth noting that
the behaviour is stable in *what* it does (anchor grounded before the
opening question, every time) while varying in how much else it grounds
and in what order.
