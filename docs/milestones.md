# Milestones & Task Tracker

The detailed, session-by-session breakdown of `roadmap.md`'s build order.
`roadmap.md` says *what order*; this doc says *what exactly to do* within
each step, checkbox by checkbox, so a session can start by reading "Where
to resume" below and immediately know the next concrete task — no
re-deriving scope from `vision.md`/`architecture.md` each time.

## How to use this doc

- **This is a living document, not a fixed calendar.** No real dates —
  sessions happen irregularly, and per the project's own scope, tasks will
  change as features get added or principles get reformulated. Edit this
  doc directly when that happens: add, remove, reorder, or rewrite tasks.
  Don't preserve stale tasks for history's sake — `git log` already keeps
  that history.
- **Check off tasks as they're completed** (`- [x]`). Leave a one-line note
  next to anything that turned out differently than planned, so the next
  session isn't surprised.
- **When a change here is actually architectural** (not just re-scoping a
  task, but changing a principle from `architecture.md`/`vision.md`, or a
  provider/schema choice), log it in `decisions.md` too — this doc tracks
  *what to do*, `decisions.md` tracks *why*.
- **Update "Where to resume" at the end of every session**, even a short
  one — that line is what makes the next session able to start cold.

## Where to resume

**Status: Milestone 11 complete.** Next up: Milestone 12 — additional AI
providers (`roadmap.md` step 12): evaluate at least one alternative
realtime voice provider per the provider-resilience decision
(`decisions.md` #2/#5), confirming a switch doesn't touch
`domain-model.md` data. The backend now has three live consumers of
`tools_interface.TOOLS`: the text loop, the voice loop, and (as of
Milestone 11) an MCP server (`mcp_server/server.py`) exposing all 18
tools generically over stdio to secondary clients like Claude
Desktop/Code — validated end-to-end via a real subprocess against the
real vault and `mistakes.db` (`decisions.md` #24). Language-Lab's real
English mistake data is imported into `mistakes.db` and flows through the
same `recommend_review`/Career-coaching machinery as every other domain
(`decisions.md` #23); `retrieve_vocabulary` stays an honest stub (no
source data exists) — and, as of Milestone 11, is exposed as such over
MCP too (a stub call surfaces a real MCP error, not a faked success).
Carried-forward known gaps, not bugs: voice sessions still can't persist
mistakes (`save_mistake` doesn't reliably fire over the Realtime API —
`decisions.md` #22); `_infer_domain` doesn't detect a specific language
from a vault-triggered session, so new language mistakes caught in normal
conversation won't auto-join the language-import bucket (`decisions.md`
#23); cross-domain interleaving isn't implemented in the session planner;
`MistakeEntry.corrected` never flips to `True`; registering the server
with Claude Desktop/Code itself is left for the user to try whenever
convenient (config snippet below), not blocking since the protocol layer
is already validated for real. See `decisions.md` #9–24 for the choices
made so far.

---

## Milestone 0 — Project setup (prerequisite to `roadmap.md` step 1)

Not itself one of `roadmap.md`'s numbered steps — the scaffolding those
steps assume already exists.

- [x] Choose backend language/framework: Python + FastAPI, dependency
  management via `uv`. Logged in `decisions.md` #9.
- [x] Choose persistence approach for mistake/session/profile data: SQLite
  as the live store, with periodic backups plus a git-tracked flat-file
  export for a diffable audit trail. Logged in `decisions.md` #10. (Not
  wired up yet — that's Milestone 1/6's job; this milestone only needed the
  decision made.)
- [x] Decide where the backend runs: local process (`uv run`) for initial
  development. Logged in `decisions.md` #11.
- [x] Basic project scaffold: `backend/pyproject.toml`,
  `backend/src/learning_os/main.py` (FastAPI app + `run()` entrypoint,
  wired as the `learning-os` script), dev-running section in the root
  README.
- [x] Minimal test setup: pytest + httpx, one passing test
  (`backend/tests/test_main.py`), `uv run pytest` documented in the README.

**Definition of done:** a backend project exists that runs, has an obvious
place to add each module from `architecture.md`, and the two open decisions
above are logged in `decisions.md`. **Done** — `uv run learning-os` serves
`GET /` returning `{"status": "ok", "service": "learning-os"}`; `uv run
pytest` passes. Module folders (retrieval/mistakes/sessions/tools-interface)
are deliberately not created yet — that's Milestone 1's explicit task, not
this one's.

---

## Milestone 1 — Backend service (`roadmap.md` step 1)

- [x] Lay out module boundaries per `architecture.md`'s modular-architecture
  list: `backend/src/learning_os/{retrieval,mistakes,sessions,
  tools_interface}/` created as empty packages (hyphen in "tools-interface"
  isn't valid in a Python module name, hence the underscore).
- [x] Config/env handling for API keys and the vault path: `config.py`'s
  `Settings` (pydantic-settings, reads `.env`/env vars) holds `vault_path`
  and `openai_api_key` — generic settings object, no provider-specific
  logic baked outside its own module. `.env.example` documents the two
  vars.
- [x] Health-check / run entrypoint: `GET /health` reports config-load
  status, whether `vault_path` resolves to a real path, and whether an
  OpenAI key is set (booleans only — never echoes the key itself).

**Definition of done:** process runs; module boundaries exist; nothing
provider-specific leaks outside its own module yet (nothing to leak yet,
but the folder structure shouldn't invite it later). **Done** — verified
live: `uv run learning-os` with `VAULT_PATH` set serves a `/health` that
correctly reports `config_loaded`, `vault_path_exists`, and
`openai_api_key_set`; `uv run pytest` passes (3 tests total, including two
new `/health` cases with and without config present).

---

## Milestone 2 — Obsidian retrieval (`roadmap.md` step 2, `retrieval.md`)

- [x] Note loader: `backend/src/learning_os/retrieval/loader.py` parses
  vault markdown files, `[[wikilinks]]` (incl. piped aliases, excluding
  image embeds), and leading YAML frontmatter (gracefully falling back to
  `{}` on absence or malformed/non-dict YAML — never crashes the whole
  vault load on one bad file).
- [x] Implement `search_notes` — naive weighted keyword/token scoring
  (title/tags/body), no external library or embeddings. Logged as
  `decisions.md` #12 (interim/provisional, same status as #11).
- [x] Implement `get_note` — case-insensitive title lookup, returns full
  content + frontmatter + tags + outgoing links.
- [x] Implement `related_notes` — 1-hop, **bidirectional** (outgoing links
  + backlinks, deduped, self excluded); 2-hop and embeddings deliberately
  deferred per this doc's own note.
- [x] Manually validated against real vault content
  (`~/Documents/Obsidian-Digital-Brain`, 1441 notes) across two domains:
  AI/ML (`Adam optimizer` ↔ `Gradient descent`, the latter reached mainly
  via backlinks — proves bidirectionality matters) and language
  (`TURKISH ROADMAP` → `Turkish alphabet` ← `Turkish Study Plan`). See
  `backend/tests/test_retrieval_real_vault.py` for the automated regression
  version of this same validation.

**Definition of done:** all three functions return correct results against
real vault notes in at least two domains. **Done** — `uv run pytest` passes
43 tests (loader unit tests incl. real vault edge cases like the
no-closing-`---` file and zero-byte notes; index unit tests on synthetic
notes; real-vault integration tests across both domains, skipped
automatically if the vault isn't present on the machine running them).

---

## Milestone 3 — Tool/function architecture (`roadmap.md` step 3, `tools.md`)

- [x] Define the function-calling contract as actual code interfaces (names,
  params, return types): `tools_interface/registry.py`'s `Tool`
  dataclass + `TOOLS: dict[str, Tool]` + `call_tool(name, **kwargs)`
  dispatcher, populated at import time in `tools_interface/__init__.py`
  from all 18 functions named in `tools.md`, each with real Python type
  hints (and pydantic models — `MistakeEntry`, `SessionPlan`/`SessionSummary`,
  `MasteryEstimate`, `JobFitAnalysis` — for the structured ones) rather than
  just the prose list.
- [x] Wire Milestone 2's three retrieval functions behind that contract —
  `search_notes`/`get_note`/`related_notes` registered directly from
  `learning_os.retrieval`, no reimplementation.
- [x] Stub every other function from `tools.md`. Mistakes and sessions each
  got their own module (`mistakes/service.py`, `sessions/service.py`,
  matching `retrieval/service.py`'s pattern — typed signatures per
  `domain-model.md`'s `MistakeEntry` fields and milestones.md M4's session
  fields, bodies raise `NotImplementedError` naming the milestone that
  implements them). Progression, Language module, Stats, and Career don't
  have a dedicated module yet (no milestone has created one), so their
  stubs live provisionally in `tools_interface/stubs.py` — expect these to
  move out into their own modules once Milestones 6/9/7 actually implement
  them.

**Definition of done:** one consistent interface exists that a model could
call today, with real retrieval behind three functions and honest stubs
behind the rest. **Done** — `call_tool("search_notes", query=...)` dispatches
to the real Milestone 2 implementation; `call_tool` on any of the other 15
names raises a `NotImplementedError` naming which milestone implements it;
an unknown tool name raises `KeyError`. `uv run pytest` passes 53 tests
(3 new files covering the registry's completeness/dispatch behavior and
each stub module's honest-failure behavior). No FastAPI routes or JSON-schema
generation were added — that's Milestone 7 (Realtime function-calling) and
Milestone 11 (MCP)'s job to build on top of this registry, not this one's.

---

## Milestone 4 — Session planner (`roadmap.md` step 4, `learning-engine.md`)

- [x] Implement the session data model from `domain-model.md` (objective,
  concepts to review, target difficulty, expected duration) — already
  existed as `sessions/models.py`'s `SessionPlan` since Milestone 3, no
  change needed.
- [x] Implement `create_session` using retrieval (mistake data doesn't
  exist yet at this point — that's fine, plan without it for now):
  `target_difficulty` is a fixed `"beginner"` default and
  `expected_duration_minutes` is derived only from concept count (5 min/
  concept, 15 min floor) — both honestly provisional until Milestone 6
  gives mastery data to inform them for real.
- [x] Build planning heuristic v1 — doesn't need to be smart, just
  functional: anchor on `search_notes(topic, limit=1)`'s best match, expand
  via `related_notes(anchor)` up to `max_concepts` (default 5). Raises
  `ValueError` if the topic matches no vault note at all — a session with
  no real grounding isn't a session, not a case worth faking a plan for.
- [x] While here: corrected `finish_session`/`summarize_session`'s stub
  docstrings, which had over-claimed "Milestone 4" back in Milestone 3 —
  this milestone's task list only ever covered `create_session`; the other
  two now point at Milestone 5, where `learning-engine.md`'s session-ends
  step (summary generation, memory update) actually lives.

**Definition of done:** `create_session` produces a real plan grounded in
actual vault content, even with a naive heuristic. **Done** — validated
against the real vault across two domains: `create_session("Adam
optimizer")` → `['Adam optimizer', 'Gradient descent', 'Optimizer',
'Optimizers & Training Mechanics']`; `create_session("Turkish alphabet")` →
`['Turkish alphabet', 'TURKISH ROADMAP', 'Turkish Study Plan']`. `uv run
pytest` passes 56 tests (synthetic-vault unit tests for the heuristic,
max_concepts capping, and the no-match error path, plus a real-vault
regression test).

---

## Milestone 5 — Text-only conversations (`roadmap.md` step 5)

- [x] Wire planner + retrieval + tool-calling into a minimal text chat loop
  (CLI is enough) against a text-capable LLM — no realtime API yet.
  `conversation/loop.py`'s `start_session`/`send_message`/`end_session`
  (plus a real interactive `run()` CLI, `uv run learning-os-chat`) call
  `create_session` (Milestone 4) to open, expose exactly the 3 real
  retrieval tools to the model via OpenAI function-calling (Milestone 2/3),
  and call `finish_session`/`summarize_session` (now real, not stubs — see
  below) to close. LLM: OpenAI Chat Completions, `decisions.md` #14.
- [x] Implement the actual teacher-style behavior from `learning-engine.md`:
  encoded as explicit rules in `conversation/prompt.py`'s system prompt
  (ask-before-tell, immediate correction, no lecturing, ground in vault
  content via tools, revisit shaky concepts before ending, open naturally).
  `sessions/service.py` gained a real in-memory transcript
  (`record_turn`/`_SESSIONS`, process-local — no persistence milestone has
  been built yet) so `finish_session`/`summarize_session` are real: summary
  is naive-but-real (which plan concepts were actually mentioned across the
  transcript), consistent with Milestone 4's own "doesn't need to be smart"
  precedent rather than adding LLM-based summarization.
- [x] Ran 4 real sessions (1 more than required) across 3 domains: AI/ML
  (`Adam optimizer`), language (`Turkish alphabet`), and chemistry
  (`Reaction Rate`, run twice — once before and once after a prompt fix, see
  check-in below).
- [x] **Pedagogy check-in** (2026-08-10): **Mostly passes, with one real gap
  found and fixed, not just noted.**
  - **Asking for production before answering:** yes, consistently across
    all 4 sessions — every opening and follow-up was a question ("how would
    you explain X"), never a lecture opener.
  - **Immediate correction — the actual finding:** session 1 (Adam
    optimizer) and session 2 (Turkish alphabet) both correctly caught and
    corrected wrong claims in the very next reply, grounded in real note
    text (e.g. "29 letters... 8 vowels and 21 consonants," not the
    learner's guessed "26, same as English"). Session 3 (Reaction Rate)
    broke this: when the learner said *"if I raise concentration, rate goes
    down... right?"* — a wrong claim hedged as a question — the model
    **let it slide** and pivoted to its next planned question instead of
    confirming or correcting it. This is exactly the failure mode
    `pedagogy.md` warns about (a claim going unaddressed, not a lecture,
    but the same practical effect: an error left standing). Root cause:
    the original prompt's rule 2 said to address wrong statements but
    didn't say what to do when a wrong claim is phrased as a tentative
    question rather than a flat assertion, and the model treated it as
    "already implicitly handled by moving on."
  - **Fix applied, not just logged:** `prompt.py` rule 2 rewritten to
    explicitly require confirming or correcting a claim — hedged or not —
    before pivoting to a new question. Re-ran the *exact same* failing
    exchange afterward: the model now responds "No — that's incorrect.
    Higher concentration usually makes the rate go up, not down" before
    continuing. Fix verified against the real case that exposed it, not
    just assumed to work.
  - **Revisit shaky concepts before ending:** present in all sessions (a
    recall check before wrap-up each time), though generic ("what's one
    thing you remember") rather than always targeting the specific concept
    that was shakiest that session — a real but minor limitation, not
    blocking.
  - **Grounding in vault content:** confirmed genuine, not just claimed —
    corrections consistently quoted actual note wording (letter counts,
    Ç/Ğ pronunciation, Adam's "smarter version of gradient descent"
    phrasing), meaning the model was actually calling `search_notes`/
    `get_note`/`related_notes` rather than relying on general knowledge.
  - **One unrelated minor observation, not fixed:** the model occasionally
    (twice, out of ~20 assistant turns across all runs) emitted a single
    reply with its own sentence duplicated verbatim
    (`"Hi! ...?\nHi! ...?"`). Looks like an OpenAI-side decoding quirk, not
    a bug in `loop.py` (tool-calling and multi-turn state were correct in
    the same runs) — worth a `.strip()`-adjacent look during later polish,
    not blocking this milestone.

**Definition of done:** a real, unscripted text conversation that plans,
quizzes, produces a session summary, and passes the pedagogy check-in above.
**Done** — `uv run pytest` passes 65 tests, fully offline/mocked (no real
API calls in the automated suite); 4 real sessions run across 3 domains: all
produced real `SessionSummary` objects, and the one pedagogy gap the check-in
found was fixed and re-verified against the real failing case, not just
documented.

---

## Milestone 6 — Mistake-memory updates (`roadmap.md` step 6, `domain-model.md`)

- [x] Implement `save_mistake` / `search_mistakes` / `get_recent_mistakes`
  against the schema in `domain-model.md`: real SQLite persistence
  (`mistakes/store.py`, stdlib `sqlite3`, fulfilling `decisions.md` #10),
  `MistakeEntry` gained a `domain: str` field it was missing
  (`decisions.md` #17).
- [x] Wire mistake detection into Milestone 5's loop — when the agent flags
  an error mid-conversation, it gets saved, not just mentioned.
  `conversation/loop.py`'s `CONVERSATION_TOOLS` now includes `save_mistake`
  (and `get_recent_mistakes`, so the model can check known gaps at session
  start); `prompt.py` instructs the model to call it on every correction,
  using the session's real (server-inferred) domain.
- [x] Wire `recommend_review` / `estimate_mastery` (reading saved mistakes)
  back into Milestone 4's planner — `create_session(topic: str | None =
  None)`: omitted topic now falls back to `recommend_review()`'s top pick,
  raising `ValueError` if nothing's recommended yet (the realistic state
  right after this shipped, before real usage accumulates). Both functions
  — plus `get_learning_profile` — moved from `tools_interface/stubs.py`
  into `mistakes/service.py` since they're entirely mistake-data-derived
  (`decisions.md` #17). `MasteryEstimate.mastery` renamed to
  `conceptual_understanding` + a new `mistake_count` field, resolving the
  scope-honesty gap `decisions.md` #15 had flagged but not yet acted on.
- [x] Verify the loop closes for real: a mistake made in one session
  visibly changes what the next session's planner chooses to review.
  Verified with real data, not just unit tests (see below).

**Definition of done:** the mistake-memory → planner feedback loop is
demonstrably closed, not just each half built in isolation. **Done** —
`uv run pytest` passes 85 tests, fully offline. Real end-to-end run: a
session on `Adam optimizer` (domain `classical-ml`) got the deliberately
wrong claim "Adam is basically just gradient descent but faster, right?",
corrected it immediately per the Milestone 5 pedagogy rules, and called
`save_mistake` — confirmed by querying the live SQLite DB directly
afterward (not assumed):
```
classical-ml|Adam optimizer|Described Adam as 'basically just gradient
descent but faster.' The note says Adam is a smarter version of gradient
descent with memory of past descent (momentum) and an adaptive learning
rate, not merely generic faster gradient descent.|conceptual confusion|medium|0.93
```
Immediately afterward, `create_session(topic=None)` — automatic mode —
proposed exactly that concept: `objective="Review Adam optimizer (due for
review) and related concepts"`, `domain="classical-ml"`. The loop closes
with real data, not a synthetic fixture.

---

## Milestone 7 — Career/CV coaching (`roadmap.md` step 7, `tools.md`'s
Career functions)

- [x] Implement `summarize_skills_for_cv` — read the learner profile
  (`domain-model.md`, `mistakes/service.py`'s `get_learning_profile`,
  now domain-optional per `decisions.md` #18) and produce a CV-ready
  summary of actual technical strengths, grounded in tracked mastery rather
  than self-reported skill level. Filters to concepts with
  `mistake_count > 0` and `conceptual_understanding >= 0.7`; returns an
  honest "not enough tracked history" message rather than fabricating
  content when nothing qualifies (real behavior when run against only the
  session's genuine, high-confidence mistakes — see below).
- [x] Implement `analyze_job_fit` — take a target job description as input,
  compare its stated requirements against the learner profile via a real
  LLM call (semantic matching against free-form prose, unlike Milestone
  5's naive substring-based `summarize_session` — `decisions.md` #18
  explains why the same "keep it naive" precedent didn't apply here), and
  return matching strengths / gaps.
- [x] Validated against a real (synthetic, per this session's decision) job
  description — see the real transcript below. New `career/` module
  (`models.py`/`prompt.py`/`service.py`/`cli.py`, `uv run
  learning-os-career`), following Milestone 6's exact precedent: implement
  for real, move out of `tools_interface/stubs.py`.

**Definition of done:** given a real job posting, the assistant produces a
CV skills summary and an honest gap list, both grounded in real mastery
data rather than guesswork. **Done** — `uv run pytest` passes 94 tests,
fully offline. Real validation, in order:
1. Enriched the real profile with 2 more live conversation sessions
   (`Turkish alphabet`, `Gradient descent`), each with a deliberate mistake
   — real `mistakes.db` then held 3 domains (`classical-ml`, `languages`,
   `math-foundations`), all genuine high-confidence corrections.
2. `summarize_skills_for_cv()` against just that real data returned the
   honest empty-state message — *none* of the 3 crossed the strength
   threshold, correctly, since they were real, confidently-flagged
   mistakes, not solid concepts.
3. Added one more entry directly (confidence 0.15, simulating a minor
   slip) to also exercise the populated path against a real LLM call:
   > "**Classical ML:** Demonstrated understanding of **optimizers**
   > through tracked review, with solid conceptual grasp (**0.85**
   > understanding) and limited errors (**1** mistake) during tutoring
   > sessions."
4. `analyze_job_fit()` against a synthetic junior-ML-engineer posting
   (gradient-based optimization, neural net training, Kubernetes, SQL,
   multilingual/localization) correctly returned `Optimizer` as the one
   matching strength and folded `Gradient descent`/`Adam optimizer`/
   `Turkish` — all real tracked entries, but weak — into the gap
   description alongside genuinely untracked skills (Kubernetes, SQL) —
   distinguishing "topic touched" from "topic mastered" rather than
   forcing a false match on topical overlap alone.

---

## Gate — re-check `pedagogy.md` before voice (per `roadmap.md`)

- [x] Reviewed all real session logs across Milestones 5–7 (~7 real
  sessions, not just 5–6 as originally scoped — Milestone 7 also produced
  real conversation data worth including) against `pedagogy.md`'s
  realistic-goals criteria. Full review: `decisions.md` #19.
- [x] Explicit decision, logged in `decisions.md` #19: **GO**. Recall-testing
  is consistently real (corrections happen in-turn, grounded in actual
  note content, including one gap found-and-fixed-and-reverified in
  Milestone 5); conceptual-understanding scoping shows up in real generated
  output, not just docs. Two non-blocking notes carried forward rather than
  silently dropped: cross-domain interleaving isn't actually implemented in
  the planner yet (confirmed against real behavior, not assumed — a
  backlog item, not a blocker); `corrected`/`save_mistake` domain-trust
  limitations from Milestones 6–7 still stand.

---

## Milestone 8 — OpenAI Realtime integration (`roadmap.md` step 8)

- [x] Get a working realtime smoke test in this project's context. Used
  the `openai` SDK's own built-in `client.realtime.connect()` rather than
  hand-rolling WebSocket code (`decisions.md` #20) —
  `Language-Lab/realtime-test/` stayed the reference for the audio
  pipeline (PipeWire echo-cancel + `parec`/`paplay`), ported to Python via
  `asyncio.create_subprocess_exec` in `realtime/audio.py`.
- [x] Wire Milestone 3's tool/function contract into the Realtime API's
  function-calling shape: `realtime/tools.py`'s `to_realtime_tools` (the
  flat `{"type":"function","name":...}` shape, confirmed different from
  Chat Completions' nested envelope before writing any code). Scoped to
  the 3 retrieval tools only (`search_notes`/`get_note`/`related_notes`)
  — `save_mistake`/session-lifecycle wiring is Milestone 9's explicit job,
  not this one's (`decisions.md` #20).
- [x] Handle session config: voice (`marin`, configurable), output
  modalities, and interruption — barge-in cancels the response
  server-side (`connection.response.cancel()`) *and* cuts local playback
  (`speaker.restart()`), improving on the reference script which only did
  the local half.

**Definition of done:** a live voice call can trigger at least one real
backend tool call (e.g. `search_notes`) and speak back a real result.
**Done** — validated for real, not assumed: `uv run pytest` passes 99
tests (the WebSocket connection, session config, event loop, and audio
subprocess plumbing are explicitly *not* offline-tested — stated as a real
boundary in `decisions.md` #20, not silently skipped). Real validation
(text input standing in for human speech — see #20 for why): confirmed
`gpt-realtime-mini` availability against the live model list; a real
session over text input triggered a real `search_notes` → `get_note` tool
chain (the model chained both unprompted before answering), produced a
real transcript carrying the same teacher-style prompt behavior from text
sessions ("...Now, how would you explain what the gradient is?"), and
477,600 bytes of real PCM16 24kHz audio, verified as a valid WAV file, not
just assumed non-empty. Separately confirmed the `pactl`/`parec` audio
subprocess plumbing itself spawns, captures real bytes, and cleans up
completely (`pactl list` showed no leftover virtual devices afterward). A
real human-voice round trip is Milestone 9's job, or `uv run
learning-os-voice` right now since this machine has real audio hardware.

**Follow-up after real use (`decisions.md` #21):** user tried
`learning-os-voice` for real and found two real gaps — no `backend/.env`
existed yet (fixed: created from `.env.example` with the real vault path),
and no way to review a session's transcript or tool calls afterward (fixed:
`realtime/session_log.py`'s `SessionLog` writes a per-session log to
`logs/<session_id>.log`, and tool calls now print live too). Not part of
Milestone 9's scope — this is a local convenience log, not domain-model
persistence.

---

## Milestone 9 — Voice conversations (`roadmap.md` step 9)

- [x] Port the full session loop (plan → converse → detect mistakes →
  summarize → update memory) from text (Milestones 5–6) to voice.
  `TUTORING_TOOLS` (`conversation/prompt.py`) is now the single shared
  tool list both loops use — closes a real drift risk (`realtime/loop.py`
  had gone stale, missing `save_mistake`/`get_recent_mistakes` since
  Milestone 6). `record_turn`/`finish_session`/`summarize_session` wired
  into `realtime/loop.py`'s event loop, reusing `sessions/service.py`
  unchanged. **"Update memory" is the one part that isn't actually
  achieved yet — see the honest finding below, not glossed over.**
- [x] Handle teacher-style interruption specifically for voice (real
  barge-in, not just a text-loop analog) — **already done in Milestone 8**
  (`connection.response.cancel()` + `speaker.restart()`); nothing new
  needed here, noted rather than re-implemented.
- [x] Run at least 3 full voice sessions across 2 domains — ran 5 real
  sessions total (3 required + 2 diagnostic, see below).

**Definition of done:** parity with Milestone 6's text loop, voice-driven,
same pedagogy check applied. **Partially done — stated honestly, not
claimed as full parity.** Real validation (`decisions.md` #22), 5 real
sessions:
- **Confirmed full parity**: conversational mistake correction (4/4 real
  sessions caught and corrected wrong claims in-turn, grounded in real
  note content); transcript recording → real session summaries;
  automatic mode (`topic=None`) correctly picked `Turkish alphabet` via
  `recommend_review()` — the actual weakest tracked concept — proving
  Milestone 6's planner-feedback loop works identically over voice.
- **Real gap, not fixed**: `save_mistake` never fired in any of 4 separate
  real attempts (original prompt, a strengthened "mandatory" rewrite,
  tested against both `gpt-realtime-mini` and full `gpt-realtime`) —
  confirmed via direct SQLite queries each time, not assumed. The same
  instructions work reliably via Chat Completions (text mode). Decided
  with the user: document this as a known, unresolved Realtime-API
  limitation rather than chase a backend-triggered nudge heuristic now.
  **Concretely: mistakes corrected in a voice session are not currently
  persisted to `mistakes.db`, so they don't inform future
  `recommend_review`/`estimate_mastery` the way text-session mistakes do.**
  Voice today has a real teaching loop, not yet a real memory loop —
  worth revisiting as a follow-up, not scheduled to a specific future
  milestone yet.
- **Pedagogy check-in** (same criteria as Milestone 5's check-in and the
  pre-voice gate, `decisions.md` #19): recall-testing holds up identically
  over voice — real corrections, grounded in vault content, not
  lecture-and-affirm. Conceptual-understanding scoping unchanged (no new
  concern). Consistency-over-baseline still not assessable (no
  longitudinal usage yet, correctly not forced). The mistake-persistence
  gap above is a real pedagogical-loop concern worth tracking, but it's a
  *memory-update* gap, not a *recall-testing* gap — the teaching behavior
  itself passes the same bar text did.

---

## Milestone 10 — Language coaching integration (`roadmap.md` step 10)

- [x] Design the integration contract between `tools.md` and
  `Language-Lab`'s existing tracked files (`ROADMAP.md`, `MISTAKES.md`,
  `PRACTICE_LOG.md` per language). Regexes verified against all 4 real
  languages' real files before any code was written.
- [x] Decide: read Language-Lab's files directly, or build an adapter that
  translates them into this project's `domain-model.md` schema? **Decided,
  then reversed after discussion, before implementation**: import
  `MISTAKES.md` as real `MistakeEntry` rows (`language/importer.py`,
  reusing `save_mistake` unmodified) rather than a permanent read-only
  lookup — logged in `decisions.md` #23 with the full reasoning (real
  scheduling/Career-visibility payoff a read-only adapter wouldn't give,
  since the source data is test entries with nothing precious to preserve
  exactly-as-is).
- [x] Implement `get_language_profile` / `get_curriculum` /
  `retrieve_vocabulary` against real Language-Lab data.
  `get_language_profile` combines the imported mastery data (via
  Milestone 6/7's existing `get_learning_profile`) with a live read of
  `PRACTICE_LOG.md` (`recent_practice`) and `ROADMAP.md`
  (`roadmap_status`) — only the mistakes half needed converting; the
  other two are session-narrative/syllabus-status, not mistakes, no
  schema conflict. `retrieve_vocabulary` stays an honest stub — confirmed
  no vocabulary-tracking file exists anywhere in Language-Lab.

**Definition of done:** a Personal Learning OS session can pull real
Language-Lab practice history into its planning, for at least one
language. **Done** — `uv run pytest` passes 125 tests. Real validation:
`uv run learning-os-language-import` imported exactly 6 real English
mistake entries into the actual `mistakes.db` (confirmed idempotent — 0 on
re-run); `recommend_review()` afterward interleaved language concepts with
vault-domain ones by weakness, not just in theory; a real conversation
session — checked by inspecting `state.messages` directly, not inferred
from the reply's wording — showed the model actually calling
`get_language_profile("English")` and `get_curriculum("English")`, with
the real imported data (the "make + object" pattern, "Grammar Precision —
In progress") visibly shaping its opening question. Known limitation
flagged, not fixed: `_infer_domain` doesn't yet detect a specific language
from a vault-triggered session, so newly-caught mistakes from natural
conversation won't automatically join the same per-language bucket this
import created (`decisions.md` #23).

---

## Milestone 11 — MCP server (`roadmap.md` step 11, `mcp.md`)

- [x] Thin transport layer wrapping the existing `tools.md` contract — no
  new logic, per `mcp.md`. `mcp_server/server.py`: one generic loop over
  `tools_interface.TOOLS`, no per-tool wrappers; all 18 tools (including
  stubs) exposed identically. See `decisions.md` #24.
- [x] Test from a real secondary client with a real query. Validated with
  the SDK's own `ClientSession` two ways: in-process (`InMemoryTransport`,
  the offline pytest suite) and a genuine OS subprocess (`stdio_client`
  spawning `uv run learning-os-mcp`) against the real vault and
  `mistakes.db`. Claude Desktop/Code registration is a config-file change
  left for the user to try at their convenience (see `decisions.md` #24);
  not blocking since the protocol layer is already validated end-to-end.

**Definition of done:** "what did I get wrong on graph algorithms last
week" is answerable from outside the voice app. **Met** — real subprocess
validation: `search_notes("graph")` returned the real vault note,
`get_recent_mistakes` returned real imported mistake data, both over the
actual stdio transport a secondary client would use.

**Try it yourself in Claude Desktop or Claude Code** (restart the app
after editing its MCP config for the change to take effect):

```json
{
  "mcpServers": {
    "learning-os": {
      "command": "uv",
      "args": ["run", "learning-os-mcp"],
      "cwd": "/home/knife/Projects/Personal-Learning-OS/backend"
    }
  }
}
```

---

## Milestone 12 — Additional AI providers (`roadmap.md` step 12)

- [ ] Evaluate at least one alternative realtime voice provider, per the
  provider-resilience decision (`decisions.md` #2/#5).
- [ ] Confirm switching providers doesn't require touching
  `domain-model.md` data — this is the actual validation of the
  provider-resilience ADR, not just a stated principle.

**Definition of done:** a second provider works end-to-end without any
change to durable data or the `tools.md` contract.
