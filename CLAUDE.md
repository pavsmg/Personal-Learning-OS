# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in
this repository.

## Purpose

Personal Learning OS: a personal voice assistant for cross-domain learning,
review, and knowledge organization built on top of the user's Obsidian
vault. See `docs/vision.md` for the full picture.

## Current state

**Build in progress — Milestone 7 of the roadmap complete.** The backend
(`backend/`, Python + FastAPI) implements the tool registry, retrieval, a
pedagogy-checked text-only conversation loop against a real LLM, real
SQLite-backed mistake memory feeding back into the session planner, and
Career/CV coaching reading real tracked mastery data. Voice (Milestone 8)
is next, gated on revisiting `docs/pedagogy.md` first per `docs/roadmap.md`.
`docs/roadmap.md`
has the intended build order; `docs/milestones.md` breaks that into
checkable tasks and tracks exactly where things stand — check its "Where to
resume" section at the start of a session, and update it at the end of one,
even a short one. Don't start implementing steps out of order without
checking with the user first.

## Working here

- Read `docs/architecture.md` before writing any backend code — the
  "backend owns the logic" and provider-resilience principles there are
  meant to constrain how modules get structured from the start, not
  retrofitted later.
- `docs/tools.md` is the contract between the model and the backend. Keep
  functions single-purpose (per the rule stated there) rather than growing
  "god functions" as new capabilities get added.
- **Log decisions as they're made.** Any nontrivial choice (a library, a
  provider, a schema shape, a build-order change) gets a new dated entry in
  `docs/decisions.md` — Context / Decision / Status — written at the time
  the choice is made, not reconstructed afterward. Update an existing
  entry's Status (Proposed → Decided, or superseded) rather than leaving
  stale entries uncorrected.
- This project's relationship to `~/Projects/Language-Lab` is itself an ADR entry
  (`docs/decisions.md` #7) — read it before touching anything that overlaps
  with Language-Lab's scope (language practice specifically).
- Read `docs/pedagogy.md` before adding a new learning mechanism (a review
  algorithm, a quiz mode, a new session-planning heuristic) — check it
  against the evidence and limitations there rather than assuming a feature
  helps because it sounds reasonable. `docs/roadmap.md` gates the voice-MVP
  step on revisiting this doc.
