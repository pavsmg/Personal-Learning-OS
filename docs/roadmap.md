# Roadmap

Status: **not started.** This is the intended build order once work begins
— nothing below has been built yet. See `milestones.md` for the detailed,
checkable task breakdown of each step below, and its "Where to resume"
section for exactly what to pick up next.

## Initial build order

Smallest usable slice first, each step staying functional before the next
starts:

1. Backend service
2. Obsidian retrieval (`retrieval.md`)
3. Tool/function architecture (`tools.md`)
4. Session planner (`learning-engine.md`)
5. Text-only conversations — prove the loop before adding voice
6. Mistake-memory updates (`domain-model.md`)
7. Career/CV coaching (`tools.md`'s Career functions) — reads mastery/mistake
   data that only becomes real as of step 6, so it can't land any earlier
8. OpenAI Realtime integration (see "Initial real-time voice provider"
   below)
9. Voice conversations
10. Language coaching — once the Language-Lab integration below is actually
    figured out
11. MCP server (`mcp.md`)
12. Additional AI providers

Text-first is deliberate: validate the learning engine and tool-calling
loop over text before adding the complexity of realtime audio. Step 7 fits
this: it's a text-only, non-voice capability, so it belongs before the
realtime work starts, not after.

**Gate before step 8:** re-check `pedagogy.md` before starting the voice
integration. Steps 1–7 (text-only) are cheap to validate against that doc's
"realistic goals" (is the agent actually testing recall, not just
discussing?) before sinking effort into realtime audio on top of a loop
that hasn't been checked yet.

## Initial real-time voice provider

Testing starts with the OpenAI Realtime API (low latency, WebRTC,
interruptions, function calling) as the concrete first implementation —
but per the provider-resilience principle in `architecture.md`, this is a
starting point for experimentation, not a permanent commitment. Notably a
different provider than `Language-Lab`'s current choice (ElevenLabs); the
two projects are free to use different voice providers independently for
now.

## Long-form, mixed-language transcription

A later-stage capability: transcribe conversations of meaningful length
(~30 min), with clear audio, that may contain multiple languages in a
single recording, including mid-conversation language switching. After
transcription: summarize the session, detect mistakes, update memory,
enrich the learner profile.

(A narrower version of this — transcribing external/mixed-language
language-practice sessions specifically — is already in `Language-Lab`'s
backlog; this is the general form, covering any domain's conversation, not
just language practice.)

## Relationship to Language-Lab

`Language-Lab` (`~/Projects/Language-Lab`) already implements a scoped-down version
of this vision for exactly one domain: language practice. Its own
`CLAUDE.md` has an equivalent Future Ideas backlog for language-specific
extensions (sentence mining, Anki integration, benchmark comparisons,
retention tracking, an active-recall agent mode, external transcription —
several of which mirror ideas above at smaller scope).

**Decision:** for now, the two stay separate projects. `Language-Lab` keeps
evolving independently. Once this larger Personal Learning OS moves from
idea to build, `Language-Lab` gets integrated as its language-learning
module rather than rebuilt from scratch — its CEFR/curriculum/vocabulary
handling becomes one domain plugged into the bigger system, not a
duplicated feature of it. See `decisions.md` for the ADR record of this
choice.
