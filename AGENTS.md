# AGENTS.md

## Project

Personal Learning OS is a local Python/FastAPI backend for a voice and text
learning coach over the user's Obsidian vault. It grounds tutoring in vault
notes, records mistakes and session-graded evidence in SQLite, schedules
review, integrates Language-Lab practice history, and exposes the same tools
through text, voice, and MCP clients.

Milestones 1-11 are complete. Milestone 12, evaluating a second realtime
provider without changing durable data or the tool contract, is blocked until
a second provider API key is available. Do not work out of the documented
roadmap order without user approval.

## Start And Finish Every Session

1. Read `docs/milestones.md`, especially **Where to resume**, and
   `docs/backlog.md` before choosing work.
2. Read the documentation relevant to the change before editing. Backend work
   always requires `docs/architecture.md`; tool changes require
   `docs/tools.md`; data or scheduling changes require `docs/domain-model.md`
   and `docs/learning-engine.md`; retrieval work requires `docs/retrieval.md`;
   new learning mechanisms require `docs/pedagogy.md`.
3. Read `docs/decisions.md` for previous rationale. Record every nontrivial
   design choice there at the time it is made, using Context / Decision /
   Status. Update a proposal's status rather than leaving it stale.
4. Update `docs/milestones.md`'s **Where to resume** at the end of the
   session, including short documentation-only sessions. Keep post-MVP work
   and pending live validation in `docs/backlog.md`, not milestones.

## Architecture Rules

- Backend code owns retrieval, session planning, scheduling, mastery
  calculations, and persistence. Models handle conversation, explanation,
  tone, and tool selection only.
- Keep provider-specific API, auth, and configuration details isolated. The
  stable `tools_interface` contract and durable data must not depend on an LLM,
  voice, transcription, embedding, or search provider.
- Keep modules narrowly scoped. Add small single-purpose tools to the registry
  rather than a combined operation or duplicated logic in text, voice, or MCP
  transport layers.
- MCP is a thin generic transport over `tools_interface.TOOLS`; do not add
  business logic or individual tool wrappers there.
- Preserve the existing Language-Lab boundary. It remains a separate project
  at `~/Projects/Language-Lab`; read ADR #7 before language-practice changes.

## Learning And Data Constraints

- The system measures conceptual understanding, not overall or applied
  competence. Do not present scores as stronger claims than the evidence
  supports.
- Preserve retrieval practice: ask for production before explaining, correct
  errors promptly, and avoid lecture-and-affirm behavior. Treat new learning
  mechanisms as pedagogy decisions, not implementation details.
- The live store is `backend/data/mistakes.db`; its rotating backup and
  tracked JSON export refresh automatically on writes. Do not casually alter,
  delete, or hand-edit durable learning data.
- The Obsidian vault is the source corpus. Its typed-relation layer is only
  partially populated, so relation-aware consumers need untyped fallbacks and
  must state the population their result covers. Never treat non-transitive
  relations as transitive.
- Voice code has known behavior pending live validation. Keep changes narrow,
  preserve non-blocking realtime dispatch, and do not claim live behavior is
  confirmed from offline tests alone.

## Layout

- `backend/src/learning_os/retrieval/`: vault loading, search, and graph
  traversal.
- `backend/src/learning_os/mistakes/`: SQLite-backed mistakes, evidence,
  scheduling, archives, and backups.
- `backend/src/learning_os/sessions/`: planning, lifecycle, and end-session
  grading.
- `backend/src/learning_os/conversation/` and `realtime/`: text and OpenAI
  Realtime clients, respectively.
- `backend/src/learning_os/tools_interface/`: provider-independent registry
  and dispatch contract.
- `backend/src/learning_os/mcp_server/`: stdio MCP transport.
- `backend/src/learning_os/language/`: Language-Lab adapter/importer.
- `backend/tests/`: offline test suite; real-vault tests skip when the vault
  is unavailable.

## Development

Run backend commands from `backend/` with `uv`:

```sh
uv run pytest
uv run pytest tests/test_some_area.py -v
uv run learning-os
uv run learning-os-chat --debug [topic]
uv run learning-os-voice --debug [topic]
uv run learning-os-mcp
```

Use `--debug` and session logs in `backend/logs/<session_id>.log` to inspect
model tool use. Automated tests must not make real API calls. Validate changed
behavior at the narrowest appropriate layer; explicitly record when a claim
still requires a real text or voice session.

Never commit secrets or `.env` files. Respect unrelated worktree changes;
this repository may be edited concurrently.
