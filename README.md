# Personal Learning OS

A personal voice assistant for natural spoken conversation to learn,
review, and organize knowledge across an entire Obsidian vault — not a
chatbot, a coach that knows the knowledge base, past mistakes, and
progression over time.

**Status: build in progress — Milestone 7 complete.** See
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
  tracker; start here each session
- [`docs/decisions.md`](docs/decisions.md) — ADR log
