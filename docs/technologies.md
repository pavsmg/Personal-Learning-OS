# Technologies & Concepts

A flat inventory of the technologies, techniques, and theory this project
touches — what's actually in use today, and what's plausible to reach for
later. Not a tutorial or a decision log (`decisions.md` has the "why" for
anything actually chosen) — just the list, kept up to date as things get
added.

## In use today

**Backend / infra**
- Python (3.14), FastAPI, uvicorn
- uv (package manager + build backend)
- SQLite (stdlib `sqlite3`) — mistake/session persistence
- pydantic-settings, PyYAML
- pytest, httpx

**AI / LLM**
- OpenAI Chat Completions API — tool/function calling, agentic loop
- OpenAI Realtime API — voice agent, WebRTC/WebSocket audio streaming
- OpenAI embeddings (`text-embedding-3-small`)
- MCP (Model Context Protocol) — stdio server exposing tools to secondary
  clients (Claude Desktop/Code)

**Retrieval / knowledge organization**
- Zettelkasten-style atomic notes + wikilinks (the Obsidian vault itself)
- Hand-rolled keyword/token search scoring (BM25-adjacent, no FTS/Whoosh)
- Embedding-based semantic similarity (domain classification)
- Graph traversal over the wikilink/backlink graph (tiered `related_notes`)
- Graph centrality (in-degree/backlink counting)
- Greedy nearest-centroid clustering (cosine similarity) for domain
  discovery

**Pedagogy / learning science**
- Retrieval practice / testing effect
- Spaced repetition — FSRS scheduling semantics (fixed constants, not
  fitted parameters)
- Desirable difficulty
- Generation effect
- Interleaving
- Elaboration / explain-in-your-own-words
- Illusion of competence / illusion of explanatory depth (as a named
  failure mode to guard against)

**Architecture patterns**
- Provider-resilience / adapter pattern (swappable LLM, embedding,
  transcription, search backends behind a stable tool contract)
- Tool-registry pattern for exposing backend functions to a model

## Could apply in the future

**Retrieval / knowledge representation**
- Vector database (dedicated ANN index, vs. current in-process similarity)
- SQLite FTS5 / BM25 proper (vs. current hand-rolled scoring)
- Knowledge graphs (typed entities/relations, vs. current untyped
  wikilinks)
- Ontologies, RDF, SPARQL
- Property graphs
- Symbolic AI / hybrid symbolic-neural reasoning
- GraphRAG (retrieval combining graph structure with vector/semantic
  search)
- PageRank-style recursive centrality (vs. current raw in-degree)
- Hierarchical/taxonomy-aware classification (broad category → subdomain)

**AI / agents**
- Multi-agent orchestration (specialized sub-agents per domain/module,
  vs. current single conversational loop)
- Additional LLM providers (Milestone 12, currently blocked — no
  second-provider API key yet)
- Alternative voice-agent providers (e.g. ElevenLabs, already
  Language-Lab's choice)
- Local/offline embedding or LLM inference

**Pedagogy / learning science**
- Two-sided evidence memory (success + failure, not just failure) —
  proposed, `decisions.md` #44
- Full FSRS parameter fitting (needs far more graded observations than
  this project currently generates)

**Architecture**
- Per-note multi-domain tagging (schema currently assumes one domain per
  note)
