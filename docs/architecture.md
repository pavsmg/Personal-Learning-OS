# Architecture

## The backend owns the logic, the model doesn't

The AI model's job is conversation, reasoning, explanation, adapting tone,
and deciding which tool to call — not owning retrieval, mastery
calculations, session planning, spaced repetition, memory storage,
statistics, or scheduling. All of that lives in the backend as durable,
provider-independent logic.

This is the principle that makes provider resilience (below) achievable at
all: swapping the LLM only ever touches the conversational layer, never the
business logic underneath it.

## Modular architecture

Specialized modules, each doing one job:

- knowledge retrieval (`retrieval.md`)
- error/mistake retrieval (`domain-model.md`)
- session planning (`learning-engine.md`)
- question generation
- real-time conversation
- evaluation
- memory
- sync
- transcription
- conversation analysis
- the language-lab module — already exists as its own scoped project (see
  "Relationship to Language-Lab" in `roadmap.md`)

Keeping these separate is what makes any one of them replaceable per
provider resilience below, and what makes it possible to build this
incrementally instead of as one monolith. See `roadmap.md` for the actual
build order across these modules.

## Provider resilience across every component, not just conversation

`Language-Lab`'s `CLAUDE.md` already has a "Provider independence"
principle, but scoped to the real-time conversation provider specifically
(currently ElevenLabs). This project extends that same principle to every
component: voice model, LLM, transcription engine, embedding engine, search
engine. Each should be swappable without touching the durable data
(knowledge, mistakes, progression) if a service's pricing changes or it
gets discontinued — the architecture needs to be modular enough for that,
not just the conversation layer.

Concretely, this means: provider-specific details (API shapes, auth,
config) stay isolated to the module that talks to that provider. The
tool/function interface (`tools.md`) and the tracked data it reads and
writes are the stable contract everything else is built against — swapping
a provider means swapping one module's implementation behind that
contract, not rewriting the contract itself.
