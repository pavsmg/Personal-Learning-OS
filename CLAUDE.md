# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in
this repository.

## Purpose

Personal Learning OS: a personal voice assistant for cross-domain learning,
review, and knowledge organization built on top of the user's Obsidian
vault. See `docs/vision.md` for the full picture.

## Current state

**Docs-only, nothing built.** This repo currently contains only the
architecture handbook in `docs/` — no source code yet. `docs/roadmap.md`
has the intended build order; don't start implementing steps out of order
without checking with the user first.

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
