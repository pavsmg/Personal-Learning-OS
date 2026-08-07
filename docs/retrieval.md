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

## Interface

Exposed to the model as `search_notes`, `get_note`, and `related_notes` —
see `tools.md`. Whatever indexing/embedding approach implements these
(full-text search, vector search, graph traversal, some combination) is an
implementation detail behind that contract, swappable per the
provider-resilience principle in `architecture.md`. No specific retrieval
technology has been chosen yet — that's an open decision, not something
this doc should pre-commit to; log the actual choice in `decisions.md` once
made.
