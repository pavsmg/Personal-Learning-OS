# Exposing the backend via MCP (later-stage, not core to the MVP)

Considered exposing the learning engine as an MCP server so other AI
surfaces (Claude Code, Claude Desktop, Cursor, future local models) could
query it directly instead of each needing a bespoke integration —
consistent with the modular-architecture and provider-resilience
principles in `architecture.md`.

Real value is for *secondary*, non-voice clients ("what did I get wrong on
graph algorithms last week," asked from Claude Desktop); it adds nothing to
the voice loop itself, since the OpenAI Realtime API's function calling
doesn't go through MCP.

Keep this late in build order (see `roadmap.md`) — worth having, not worth
building before the voice MVP works. When it does get built, it should be a
thin transport layer over the same `tools.md` function contract, not a
separate interface to design and maintain.
