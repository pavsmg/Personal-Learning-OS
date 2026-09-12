# Retrieval

The corpus this project retrieves from is the Obsidian vault
(`~/Documents/Obsidian-Digital-Brain`) itself — a Zettelkasten-style
knowledge base of ~1,000 atomic markdown notes linked by `[[wikilinks]]`,
plus numbered "roadmap" notes that act as tables of contents for a given
domain (e.g. `LINUX ROADMAP.md`, `TURKISH ROADMAP.md`). See that vault's
own `CLAUDE.md` for the note-format and linking conventions this retrieval
layer needs to work with.

## What retrieval needs to do

On a request like "quiz me on algorithms," the assistant should:

1. Retrieve the relevant atomic notes for the requested topic.
2. Understand the relationships between them (the wikilink graph, and for
   domains that have one, the roadmap note's structure/ordering).
3. Build a natural conversation from that material rather than following a
   fixed script.
4. Ask questions, ask for explanations in the learner's own words, detect
   gaps as they show up, and adapt the rest of the conversation
   accordingly.

This generalizes what a language-specific `ROADMAP.md` note already does
for one domain (grammar/vocab topics with status, in `Language-Lab`) to
every domain in the vault, including ones with no existing roadmap
structure at all (math, physics, sport) — for those, retrieval has to work
off the raw note graph rather than a curated index.

## The typed-relation layer

As of 2026-09-11 the vault carries more than untyped wikilinks. Notes
declare a `type:` (`moc`, `hub`, `concept`, `process`, `reference`) and
name their relations in frontmatter, using a closed 25-name vocabulary
specified in the vault's own `Knowledge graph relations.md` — that note is
the authority for what each name means; `decisions.md` #62 records why
this project cares.

What retrieval gets from it:

- **A real foundational ranking.** `requires` is transitive and cycle-free
  (verified), so following it gives prerequisite depth instead of link
  volume. On the typed subset this disagrees with raw backlink counting on
  6 of the top 10 — see #62 for the numbers.
- **A legal study order.** A topological sort over `requires` says what
  can be introduced before what.
- **Question shape per edge.** `contrasts-with` implies a discrimination
  question, `often-confused-with` a deliberate trap, `solves` a "why does
  this exist" question whose answer is already written in the property,
  `assumes` a boundary question. See `pedagogy.md` before turning any of
  these into a quiz mode.
- **Notes that should not anchor a session.** `type: reference` marks
  lookup material (charts, tables) where question generation produces the
  wrong kind of question by construction.

Three constraints any consumer must respect:

1. **Traversal has to be relation-aware.** `requires`, `kind-of`,
   `generalizes`, `assumes` and `supersedes` are transitive; `part-of`,
   `contrasts-with`, `causes` and the rest are **not**. Chaining a
   non-transitive relation invents facts nobody asserted.
2. **Discount out-links from `moc` and `hub` notes** — they are indexes,
   not dependencies. This alone fixes most of what #37 flagged.
3. **Coverage is partial** (~10% of notes as of writing). Typed edges are
   an enrichment over the untyped graph, not a replacement for it; an
   untyped fallback is mandatory, and any ranking must say which
   population it was computed over.

Some relation values are plain strings rather than wikilinks — `solves`
in particular is string-valued in practice, because the *problem* a
concept solves rarely has a note of its own. A consumer must handle both
shapes; the string ones are annotations, not graph edges.

The vault also uses a pre-existing `status: stub` property on ~172 thin
notes. It is not a relation, and it is a useful signal in its own right:
a stub is poor material to build a session on.

## Interface

Exposed to the model as `search_notes`, `get_note`, and `related_notes` —
see `tools.md`. Whatever indexing/embedding approach implements these
(full-text search, vector search, graph traversal, some combination) is an
implementation detail behind that contract, swappable per the
provider-resilience principle in `architecture.md`. No specific retrieval
technology has been chosen yet — that's an open decision, not something
this doc should pre-commit to; log the actual choice in `decisions.md` once
made.
