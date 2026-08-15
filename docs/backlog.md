# Post-MVP Backlog

`roadmap.md`'s 12-step build is done except for the blocked Milestone 12
(`milestones.md` tracks that one). Everything here is work that doesn't
fit either of the project's other trackers: things already implemented
and tested but whose real claim is about live model behavior, not yet
confirmed against an actual conversation; and enhancement ideas that
aren't scoped or decided yet. `decisions.md` still holds the "why" for
anything that graduates out of here into real work — this doc just keeps
the "what's still owed" list from disappearing into session-start
guesswork.

## How to use this doc

- **Living doc, like `milestones.md`.** Edit in place — add, remove,
  reorder. Don't preserve stale entries for history's sake; `git log` and
  `decisions.md` already keep that record.
- **Pending real-session validation** items get removed from here the
  moment they're confirmed — the corresponding `decisions.md` entry's
  Status flips from Proposed to Decided at the same time, so that log
  stays the single source of truth for *why* something is trusted.
- **Improvement ideas** are discussion-stage: not yet scoped, not yet
  decided. When one actually gets built, it graduates — remove it from
  here, give it a real `decisions.md` entry the way every other
  architectural choice gets one.

## Pending real-session validation

Grouped by rule, since more than one decision sometimes touches the same
rule:

- **Rule 1** — `decisions.md` #29. Stop reformulating "how would you
  explain X" after a clear "I don't know"; explain directly instead.
  Check: a real "I don't know" on unfamiliar material gets a direct
  explanation + example on the next turn, not another rephrased question.
- **Rule 5** — `decisions.md` #28, #30. Grounding source is
  domain-appropriate (vault tools vs. Language-Lab tools); word-level
  vocabulary needs no grounding lookup at all. Check: a fresh,
  never-tracked vocabulary question gets explained directly — no
  `get_note`/`search_notes` attempt, no disclosed gap.
- **Rule 10** — `decisions.md` #25 (core disclosure mechanism already
  confirmed live), refined by #28 (scope narrowed to exclude
  Language-Lab-sourced concepts). Check: the model doesn't call `get_note`
  on a curriculum/mistake label expecting a vault match, and doesn't
  disclose a vault gap for a concept it has real tracked data on.
- **Rule 11** — `decisions.md` #26. Applicative follow-up after a correct
  explanation. Not exercised at all yet — no real session so far has
  reached a correct explanation to follow up on. Check: after the learner
  gives a correct definition, the model poses a novel-scenario application
  question before moving to the next concept.
- **Rule 5 (mid-conversation grounding)** — `decisions.md` #35. Grounding
  applies to any concept about to be quizzed on, not just the planned
  list. Check: bring up a related-but-unplanned concept mid-session and
  confirm (via `--debug`/the session log) the model actually calls
  `search_notes`/`get_note`/`related_notes` for it before quizzing,
  instead of treating "not on the original list" as an exemption.
- **Rule 5 (opening-question grounding)** — `decisions.md` #41. Found
  failing live: a real `--debug` transcript showed the session's own
  anchor concept ("TCP") went ungrounded through the opening question and
  the direct explanation that followed, with `search_notes` only called
  several turns later when the learner asked for related concepts. Rules
  5 and 8 were patched to require grounding the anchor concept before the
  opening question. Check: a fresh `--debug` run on a vault-anchored topic
  confirms `search_notes`/`get_note` for the anchor concept fires before
  the opening question is sent, not after.
- **CV summary vault-importance weighting** — `decisions.md` #40. The
  data plumbing (sort by importance, `vault_importance` field in the
  prompt) is verified against real data; whether the LLM's summary
  actually leads with foundational concepts is unconfirmed. Check: once
  2+ real strengths exist with differing importance, call
  `summarize_skills_for_cv()` for real and confirm the more foundational
  one is emphasized/leads, not just listed in the same order as always.

## Improvement ideas — session planner

Discussion-stage, none of these are scoped or decided yet (opened
2026-08-12):

- [ ] **Extend the "prefer tracked data over blind graph traversal" fix
  beyond language domains.** The Turkish-alphabet-style bug (a reference
  note picked as a quiz target, `decisions.md` #31) can happen in any
  domain — there's no Language-Lab equivalent for e.g. chemistry, but
  `mistakes.db` already has real per-domain mistake data a non-language
  planner path could lean on instead of pure `related_notes` traversal.
- [ ] **Feed real mastery data into difficulty/duration** — scoped
  2026-08-15, `decisions.md` #43 (Proposed): evidence classes rather than
  an averaged scalar (the 1.0 default for untracked concepts makes an
  average lie), depth-scoped labels instead of beginner/intermediate/
  advanced, duration sized by evidence but kept out of the prompt. The
  half that carries the value is that neither field currently has a
  reader. Not built yet. Original note:
  `target_difficulty` is hardcoded `"beginner"` always;
  `expected_duration_minutes` is purely `5 × concept_count`. Both were
  explicitly flagged as provisional back in Milestone 4 ("until Milestone
  6 gives mastery data to inform them for real") — Milestone 6 shipped
  that data; the planner never came back to use it.

## Improvement ideas — retrieval / knowledge graph

- [x] ~~Weighted graph centrality core primitive~~ — done, `decisions.md`
  #37. `VaultIndex.most_important(limit)` ranks notes by backlink count;
  exposed as `most_important_notes`. Known tradeoff, still unresolved:
  raw in-degree conflates "foundational" with "generic and overused" — a
  note like `Object` or `Event` could rank high from casual cross-domain
  mentions rather than real domain centrality. PageRank-style recursive
  weighting (each in-link weighted by the linking note's own importance)
  is the named fix if raw counting proves too coarse in practice.
- [x] ~~First application: blind-spot cold-start fallback~~ — done,
  `decisions.md` #37. `create_session`'s automatic mode now offers a
  foundational, never-tracked concept instead of erroring when there's no
  mistake history to work from at all.
- [x] ~~Tiebreak within `related()`'s tiers~~ — done, `decisions.md` #38.
  Same-tier neighbors now rank by backlink count, alphabetical only as
  the tiebreak.
- [x] ~~Priority layer on top of #32/#33~~ — done, `decisions.md` #39.
  Concepts within the same overdue-urgency bucket now prefer the more
  foundational one. No case in today's real `mistakes.db` exercises it
  (only `classical-ml` has 2+ concepts, and their urgency gap is genuine,
  not close) — validated synthetically instead, same pattern #32/#33
  used before real data existed to demonstrate them.
- [x] ~~Weighting Career/CV strength summaries toward demonstrated
  mastery of hub concepts~~ — done, `decisions.md` #40. Scoped to
  `summarize_skills_for_cv` only, not `analyze_job_fit` (job relevance,
  not vault centrality, is the right signal there). All four named
  applications of the centrality primitive are now built.
