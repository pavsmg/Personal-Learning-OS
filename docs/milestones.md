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

**Status: Milestone 1 complete.** Next up: Milestone 2, first task ("Note
loader: parse vault markdown files, `[[wikilinks]]`, and YAML
frontmatter"). Backend scaffold lives in `backend/` (Python + FastAPI +
uv); see `decisions.md` #9–11 for the language/persistence/runtime choices.
Config is read from env/`.env` via `learning_os/config.py` (copy
`backend/.env.example` to `backend/.env` and set `VAULT_PATH` before
running `retrieval` work in Milestone 2).

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

- [ ] Note loader: parse vault markdown files, `[[wikilinks]]`, and YAML
  frontmatter.
- [ ] Implement `search_notes` — start with keyword/full-text search;
  embeddings/vector search is an open choice, not a prerequisite (see
  `retrieval.md`'s "no specific retrieval technology has been chosen yet").
- [ ] Implement `get_note` — fetch a single note's content + metadata.
- [ ] Implement `related_notes` — wikilink graph traversal, 1-hop to start
  (2-hop is a later refinement, not needed for a first pass).
- [ ] Manually validate against real vault content across at least two
  different domains (e.g. an algorithms/CS topic and one language roadmap)
  — retrieval that only works for one domain's note shape isn't validated.

**Definition of done:** all three functions return correct results against
real vault notes in at least two domains.

---

## Milestone 3 — Tool/function architecture (`roadmap.md` step 3, `tools.md`)

- [ ] Define the function-calling contract as actual code interfaces
  (names, params, return types) — not just the prose list in `tools.md`.
- [ ] Wire Milestone 2's three retrieval functions behind that contract.
- [ ] Stub every other function from `tools.md` (mistakes, sessions,
  language module, stats) so the full contract exists even before each
  module is implemented — callers can rely on the shape early.

**Definition of done:** one consistent interface exists that a model could
call today, with real retrieval behind three functions and honest stubs
behind the rest.

---

## Milestone 4 — Session planner (`roadmap.md` step 4, `learning-engine.md`)

- [ ] Implement the session data model from `domain-model.md` (objective,
  concepts to review, target difficulty, expected duration).
- [ ] Implement `create_session` using retrieval (mistake data doesn't
  exist yet at this point — that's fine, plan without it for now).
- [ ] Build planning heuristic v1 — doesn't need to be smart, just
  functional (e.g., pick N related notes for the requested topic via
  `related_notes`).

**Definition of done:** `create_session` produces a real plan grounded in
actual vault content, even with a naive heuristic.

---

## Milestone 5 — Text-only conversations (`roadmap.md` step 5)

- [ ] Wire planner + retrieval + tool-calling into a minimal text chat loop
  (CLI is enough) against a text-capable LLM — no realtime API yet.
- [ ] Implement the actual teacher-style behavior from `learning-engine.md`:
  ask questions, request explanations, interrupt instead of
  summarizing-after, revisit shaky concepts before the session ends.
- [ ] Run at least 3 full sessions manually, across at least 2 domains.
- [ ] **Pedagogy check-in:** review those 3 sessions against `pedagogy.md`'s
  "realistic goals" — is the agent actually asking for
  production/explanation, or drifting toward lecture-and-affirm? Write the
  answer down here (or in a short note) before moving on; if it's drifting,
  fix the prompting before Milestone 6, not after.

**Definition of done:** a real, unscripted text conversation that plans,
quizzes, produces a session summary, and passes the pedagogy check-in above.

---

## Milestone 6 — Mistake-memory updates (`roadmap.md` step 6, `domain-model.md`)

- [ ] Implement `save_mistake` / `search_mistakes` / `get_recent_mistakes`
  against the schema in `domain-model.md`.
- [ ] Wire mistake detection into Milestone 5's loop — when the agent flags
  an error mid-conversation, it gets saved, not just mentioned.
- [ ] Wire `recommend_review` / `estimate_mastery` (reading saved mistakes)
  back into Milestone 4's planner — this closes the loop.
- [ ] Verify the loop closes for real: a mistake made in one session
  visibly changes what the next session's planner chooses to review.

**Definition of done:** the mistake-memory → planner feedback loop is
demonstrably closed, not just each half built in isolation.

---

## Milestone 7 — Career/CV coaching (`roadmap.md` step 7, `tools.md`'s
Career functions)

- [ ] Implement `summarize_skills_for_cv` — read the learner profile
  (`domain-model.md`) and produce a CV-ready summary of actual technical
  strengths (e.g. database knowledge), grounded in tracked mastery rather
  than self-reported skill level.
- [ ] Implement `analyze_job_fit` — take a target job description as input,
  compare its stated requirements against the learner profile, and return
  two things: which tracked strengths to foreground for that role, and
  which required skills are gaps not yet covered by the profile.
- [ ] Validate against at least one real job description and confirm the
  gap list matches what the user already knows they're weak on — this is a
  read-only feature on top of existing data, not a new tracking mechanism,
  so it needs no schema changes to `domain-model.md`.

**Definition of done:** given a real job posting, the assistant produces a
CV skills summary and an honest gap list, both grounded in real mastery
data rather than guesswork.

---

## Gate — re-check `pedagogy.md` before voice (per `roadmap.md`)

- [ ] Review all Milestone 5–6 session logs against `pedagogy.md`'s
  realistic-goals criteria (consistency, actual recall-testing).
- [ ] Explicit go / no-go / adjust-scope decision, logged in `decisions.md`
  if it changes anything about the plan below.

---

## Milestone 8 — OpenAI Realtime integration (`roadmap.md` step 8)

- [ ] Get a working realtime smoke test in this project's context (see
  `Language-Lab/realtime-test/` for a minimal existing WebSocket example
  against the OpenAI Realtime API — a starting reference, not something
  this repo depends on).
- [ ] Wire Milestone 3's tool/function contract into the Realtime API's
  function-calling shape.
- [ ] Handle session config: voice choice, output modalities, interruption
  (barge-in) handling.

**Definition of done:** a live voice call can trigger at least one real
backend tool call (e.g. `search_notes`) and speak back a real result.

---

## Milestone 9 — Voice conversations (`roadmap.md` step 9)

- [ ] Port the full session loop (plan → converse → detect mistakes →
  summarize → update memory) from text (Milestones 5–6) to voice.
- [ ] Handle teacher-style interruption specifically for voice (real
  barge-in, not just a text-loop analog).
- [ ] Run at least 3 full voice sessions across 2 domains.

**Definition of done:** parity with Milestone 6's text loop, voice-driven,
same pedagogy check applied.

---

## Milestone 10 — Language coaching integration (`roadmap.md` step 10)

- [ ] Design the integration contract between `tools.md` and
  `Language-Lab`'s existing tracked files (`ROADMAP.md`, `MISTAKES.md`,
  `PRACTICE_LOG.md` per language).
- [ ] Decide: read Language-Lab's files directly, or build an adapter that
  translates them into this project's `domain-model.md` schema? Log as an
  ADR — this is exactly the kind of module-boundary decision worth
  recording.
- [ ] Implement `get_language_profile` / `get_curriculum` /
  `retrieve_vocabulary` against real Language-Lab data.

**Definition of done:** a Personal Learning OS session can pull real
Language-Lab practice history into its planning, for at least one language.

---

## Milestone 11 — MCP server (`roadmap.md` step 11, `mcp.md`)

- [ ] Thin transport layer wrapping the existing `tools.md` contract — no
  new logic, per `mcp.md`.
- [ ] Test from a real secondary client (Claude Desktop or Claude Code)
  with a real query.

**Definition of done:** "what did I get wrong on graph algorithms last
week" is answerable from outside the voice app.

---

## Milestone 12 — Additional AI providers (`roadmap.md` step 12)

- [ ] Evaluate at least one alternative realtime voice provider, per the
  provider-resilience decision (`decisions.md` #2/#5).
- [ ] Confirm switching providers doesn't require touching
  `domain-model.md` data — this is the actual validation of the
  provider-resilience ADR, not just a stated principle.

**Definition of done:** a second provider works end-to-end without any
change to durable data or the `tools.md` contract.
