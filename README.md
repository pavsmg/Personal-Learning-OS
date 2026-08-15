# Personal Learning OS

A personal voice assistant for natural spoken conversation to learn,
review, and organize knowledge across an entire Obsidian vault — not a
chatbot, a coach that knows the knowledge base, past mistakes, and
progression over time.

**Status: build in progress — Milestone 11 complete.** See
`docs/milestones.md` for exactly what's done and what's next. Start with
`docs/vision.md` for what this is and why, and `docs/roadmap.md` for build
order.

## Backend dev setup

The backend lives in `backend/` (Python + FastAPI, managed with
[`uv`](https://docs.astral.sh/uv/); see `docs/decisions.md` #9–11 for why).

```sh
cd backend
uv run learning-os        # starts the server on http://127.0.0.1:8000
```

`learning-os-chat` and `learning-os-voice` both accept an optional topic and a
`-d`/`--debug` flag that prints every tool call (name, arguments, and result)
as it happens, for inspecting exactly what the model is calling behind the
scenes:

```sh
uv run learning-os-chat --debug                  # let it pick a topic, show tool calls
uv run learning-os-chat --debug gradient descent # explicit topic, show tool calls
uv run learning-os-voice --debug                 # same, for a voice session
```

Omit `--debug` for a clean session with no tool-call output. Either way, every
session — text or voice — writes a full transcript with its tool calls to
`backend/logs/<session_id>.log` (gitignored). `--debug` only controls what the
terminal shows as it happens; the log is written regardless.

`mistakes.db` is the only data in this project that git can't recover, so it
gets a rotating binary backup plus a git-tracked JSON export
(`docs/decisions.md` #10, #46). Both refresh automatically whenever a mistake
is saved; run them on demand — or from cron — with:

```sh
uv run learning-os-backup                # force a backup + refresh the export
uv run learning-os-backup --export-only  # refresh the export only
```

Run the test suite (or a single test) with:

```sh
cd backend
uv run pytest                          # whole suite
uv run pytest tests/test_main.py -v    # one file
```

## Docs

- [`docs/vision.md`](docs/vision.md) — what this is, what it should feel
  like to use
- [`docs/pedagogy.md`](docs/pedagogy.md) — whether/why this should actually
  help, honestly, including the counter-arguments
- [`docs/architecture.md`](docs/architecture.md) — design principles
- [`docs/domain-model.md`](docs/domain-model.md) — core entities
- [`docs/tools.md`](docs/tools.md) — model/backend function interface
- [`docs/retrieval.md`](docs/retrieval.md) — retrieval over the vault
- [`docs/learning-engine.md`](docs/learning-engine.md) — the session loop
- [`docs/mcp.md`](docs/mcp.md) — later-stage MCP exposure
- [`docs/roadmap.md`](docs/roadmap.md) — build order
- [`docs/milestones.md`](docs/milestones.md) — detailed task-by-task
  tracker for the original build; start here each session
- [`docs/backlog.md`](docs/backlog.md) — post-MVP work: pending
  real-conversation validations and unscoped improvement ideas
- [`docs/decisions.md`](docs/decisions.md) — ADR log
