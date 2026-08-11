# Pedagogical Rationale

Everything else in `docs/` describes what this project would build. This
doc is the check on whether it's actually worth building: does the design
line up with what's known to work for learning, and where might it not?
Written to include real counter-arguments, not just supporting evidence —
a rationale that only cites evidence for what's already been designed
isn't a check, it's a rationalization.

**Gate:** revisit this doc before `roadmap.md`'s voice-MVP step (steps 8–9).
If the case for a specific piece is weak, that should change scope or
build order before code gets written around it, not after.

## What learning science actually supports

The mechanisms with real evidence behind them, relevant to this project:

- **Retrieval practice / the testing effect** — actively recalling
  something strengthens memory more than re-reading it. Being quizzed beats
  being told.
- **Spaced repetition** — review spaced out over increasing intervals beats
  massed review, for the same total time invested.
- **Desirable difficulty** — learning that feels slightly effortful (recall
  under some struggle, interleaved practice) produces better retention than
  learning that feels smooth, even though it feels worse in the moment.
- **Generation effect** — producing an answer or explanation yourself
  (versus recognizing or reading a correct one) improves retention.
- **Interleaving** — mixing topics/problem types beats blocking practice by
  type, for building transferable understanding rather than pattern-matching
  within a block.
- **Elaboration / explaining in your own words** — connecting new material
  to existing knowledge and articulating it beats passive consumption.

## Where the design maps onto that evidence

- `learning-engine.md`'s teacher-style agent (asking questions, requesting
  explanations, interrupting instead of summarizing afterward) is a direct
  implementation of retrieval practice and the generation effect — it's
  structured to force production, not just permit it.
- `domain-model.md`'s mistake-memory entries plus `learning-engine.md`'s
  session planner (deciding what to review before a session starts) is a
  spaced-repetition scheduler in different clothing — the same underlying
  mechanism as Anki's, just driven by conversational performance instead of
  card-review ratings.
- Retrieval across the *whole* vault (`retrieval.md`) rather than one topic
  per session is a deliberate opening for interleaving — cross-domain
  sessions aren't just a feature, they're the mechanism this evidence says
  should help, if the retrieval and planning layers actually mix domains
  rather than defaulting to single-topic sessions.

## Honest limitations and open risks

- **Is voice actually better, or just more appealing to build?** Anki plus
  disciplined active recall already implements retrieval practice and
  spacing with a fraction of the engineering effort and an already-proven
  track record. Nothing here has evidence that a voice-based LLM tutor
  outperforms that baseline for retention — it's an assumption this project
  is built on, not a validated finding. The honest case for voice is
  lower-friction *habit formation* (talking is easier to start than opening
  a deck) and coverage of material Anki-style cards don't fit well
  (open-ended explanation, debugging a reasoning error live) — not proven
  superior retention per unit of time invested.
- **Illusion of competence from conversational fluency.** A fluent-sounding
  conversation about a topic is not the same as being able to reproduce or
  apply it later — verbal fluency is a notoriously bad proxy for durable
  learning. `learning-engine.md`'s "interrupt when wrong, come back to shaky
  concepts" design is the right instinct here, but only holds if the agent
  is actually implemented to test recall and production, not just to
  discuss and affirm — a design intent right now, not something built and
  verified yet. Resolved into a concrete scope decision under "Realistic
  goals" below: the system claims to verify conceptual understanding of
  fundamentals, explicitly not overall competence — even that narrower claim
  isn't bulletproof (recited definitions can outrun real understanding of
  the mechanism behind them — the "illusion of explanatory depth"), which is
  exactly why interrupt-and-probe still matters rather than accepting a
  fluent answer at face value.
- **Cross-domain breadth vs. depth.** Interleaving helps *within* related
  material (e.g. mixed algorithm problem types) more reliably than it helps
  across unrelated domains in the same sitting (algorithms, then Turkish
  grammar, then squat form). A single "coach" spanning everything risks
  diluting depth for the sake of breadth if the session planner doesn't
  deliberately manage that tradeoff — this needs to be a planner design
  constraint, not an assumed benefit of the architecture.
- **No evidence for this specific combination.** Voice interface +
  cross-domain + LLM-driven adaptive tutoring, together, is not a studied
  configuration — each piece individually has some evidence base (retrieval
  practice, spacing), but their combination here is a novel design, not an
  application of a validated system. Treat the whole thing as a hypothesis
  to test against actual use, not a foregone conclusion.
- **Friction risk in the other direction.** A more elaborate system can
  paradoxically reduce practice frequency if it's more effortful to start a
  session than opening a simpler tool — `vision.md`'s "minimal interface"
  goal is explicitly trying to prevent this, but it's worth stating as a
  real failure mode: build complexity that increases time-to-first-word
  works against the entire premise.

## Realistic goals

Given the above, the honest goal for a first build isn't "prove this
improves learning outcomes" — that needs longitudinal data this project
won't have early on. A more realistic bar:

- **Conceptual understanding, not overall competence.** What a conversation
  can actually verify is whether the learner can produce a topic's
  foundational concepts on demand — definitions, mechanisms, how one idea
  differs from a related one — not whether they're skilled at applying it
  under real, unscripted conditions (solving a novel problem, executing a
  physical skill, using a language spontaneously). Conflating the two
  overclaims what conversational testing proves. Every "mastery"/"level"
  signal this system reports should be scoped to the former and should not
  imply the latter — this is the concrete resolution to the illusion-of-
  competence risk below, not just a flagged concern.
- **Consistency over the baseline.** Does having this available increase
  actual session frequency/consistency compared to current habits (ad hoc
  note review, occasional Language-Lab sessions)? This is measurable early
  and is the mechanism (spacing depends on consistency) most of the
  pedagogical case actually rests on.
- **Does the agent actually test recall, not just discuss?** A concrete,
  checkable property of any early build: sample a few sessions and verify
  the agent is asking for production/explanation rather than defaulting to
  lecture-and-affirm. If it drifts toward the latter, the core pedagogical
  premise isn't actually being implemented regardless of what this doc
  claims.
- **Don't chase retention metrics before the tool is used enough to
  generate them.** Early success criteria should be behavioral (is it being
  used, is it testing recall) — not "did retention improve," which needs
  much more usage history than an MVP will have.
