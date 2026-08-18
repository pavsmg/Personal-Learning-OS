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
- **CV summary vault-importance weighting** — `decisions.md` #40. The
  data plumbing (sort by importance, `vault_importance` field in the
  prompt) is verified against real data; whether the LLM's summary
  actually leads with foundational concepts is unconfirmed. Check: once
  2+ real strengths exist with differing importance, call
  `summarize_skills_for_cv()` for real and confirm the more foundational
  one is emphasized/leads, not just listed in the same order as always.

- **Voice open/close parity** — `decisions.md` #48. Voice now opens the
  session itself (`response.create` after `session.update`) and gets a
  spoken wrap-up when you press Enter. Offline tests cover the protocol
  messages; live behaviour is unconfirmed. Check: start `learning-os-voice`
  and say nothing — the tutor should greet and ask its first question
  unprompted; then press Enter and confirm a spoken recap arrives before
  the summary line.
- **Two-sided evidence grading over a real voice session** — `decisions.md`
  #44. The grading pass reads `logs/<session_id>.log`, the format voice
  already writes, so it's structurally able to grade a voice session the
  same as a text one (closing #22) — but that's untested against a real
  voice conversation, only against real text sessions and offline fakes.
  Check: run a real `learning-os-voice` session, let it end, and confirm
  `evidence` rows and `GRADE:` log lines appear for it exactly like a text
  session's.

## Improvement ideas — session planner

Discussion-stage, none of these are scoped or decided yet (opened
2026-08-12):

- [x] ~~Feed real mastery data into difficulty/duration~~ — done,
  `decisions.md` #43. Evidence classes (`untracked`/`shaky`/`settled`,
  split at 0.5 on `conceptual_understanding`) replace the averaged scalar;
  `target_difficulty` aggregates a session's concepts to
  `foundational`/`consolidating`/`extending`; duration is sized per-class
  (shaky costs more minutes than settled) and stays out of the prompt.
  Wired into `SYSTEM_PROMPT_TEMPLATE` via a new `Starting point:` line, so
  the values actually get read, not just computed. Thresholds and the
  none/all/mixed aggregation are v1 constants checked against real data
  (10 tracked pairs today) but not tuned — flagged in the decision entry
  as the first thing worth revisiting once real session volume gives more
  than one or two tracked concepts per domain.

- [x] ~~Phase 1: folder fallback~~ — done, `decisions.md` #49.
  `_infer_domain` now falls back to the vault's top-level folder name
  before giving up to `"general"`. Honestly scoped: verified against the
  real vault to change **zero** real notes today (every note in a topic
  folder already has a tag), and doesn't touch `TCP.md` itself (root
  note, no folder). A safety net for future folder-organized notes, not a
  fix for the present gap. The real target — 790 real root-level notes
  with neither domain frontmatter nor a tag, `TCP.md` among them — is
  phases 2 and 4 below.
- [x] ~~Phase 2: embeddings-based domain classifier~~ — done,
  `decisions.md` #51. Writes `domain:` straight into vault frontmatter
  (the user's explicit choice, against my recommendation of a
  backend-owned cache) — the first place this project mutates the vault
  instead of only reading it. Applied for real: 49 notes classified
  clean into 19 real domains. Real gotcha found and fixed before touching
  any file: the naive first pass used `infer_domain`'s existing tag
  fallback for classes and picked up organizational meta-tags, not just
  subject domains — `transconcept` (25 notes: `Object`, `Callback`,
  `Event`...) nearly became a "domain" and pulled `JavaScript`/`WebSocket`
  into it. Fixed with `MIN_CLASS_SIZE = 5` (kills one-off tag noise
  automatically) and an explicit, user-confirmed `EXCLUDED_CLASS_DOMAINS`
  set (`{"transconcept"}` today) for the well-populated-but-not-a-domain
  case a count filter can't catch. `TCP.md` itself is still unclassified,
  honestly — no `networking` class exists anywhere in the vault's real
  domain signal for it to match against, a data gap, not a threshold one.
- [x] ~~Discover new domains by clustering, seed `networking`~~ — done,
  `decisions.md` #52. `TCP.md`'s cluster had no domain because
  `networking` didn't exist as a domain anywhere in the vault, not
  because of a threshold or matching problem — so a one-off clustering
  pass (same embedding math as #51, grouping instead of matching) went
  looking for real, coherent topics among the 741 still-unlabeled notes.
  Found 9 clean clusters (≥5 notes each); user approved 8 as new domains
  (`networking`, `linux`, `javascript`, `algorithms`, `databases`,
  `computer-architecture`, `data-structures`, `bash-scripting`) and
  explicitly excluded one non-technical cluster (`masculinity-and-society`
  content) from the tutoring domain system. 70 notes seeded, then #51's
  classifier re-run against the new classes matched 32 more on its own.
  **`TCP.md` now reads `domain: networking`, confirmed directly** — the
  case that started #49 is closed. Deferred, not decided: whether a note
  can carry more than one domain — real schema change
  (`MistakeEntry`/`SessionPlan`/`recommend_domain` are all single-`str`
  today), not yet needed since none of the 9 candidate clusters actually
  overlapped with each other.
- [x] ~~Phase 3: neighbor-vote inference (`related_notes`)~~ — done,
  `decisions.md` #53, all four of #49's phases now built. Checked first
  whether it still added anything beyond #52's clustering: yes, 292 of
  the 639 remaining notes had a clear plurality domain among their real
  graph neighbors. `min_votes` tuned against real evidence, not guessed —
  `>= 2` produced 123 matches but included two real mislabels
  (`Windows`/`MS-DOS` → `linux`, from being *contrasted with* Linux, not
  part of it); `>= 3` (the shipped default) dropped to 64 and removed
  both on manual review. Two honest borderline cases applied as-is by
  user choice: `macOS`/`Android` → `linux` at full confidence — not
  noise, but a sign the `linux` domain #52 seeded reads more like
  "Unix/OS-family fundamentals" than strictly Linux. Applied for real:
  64 more notes (`UDP`, `JWT`, `init`, `ARP`, `HTTP requests`...).
  Unlabeled count: 639 → 575.
- [x] ~~Lower `min_votes` to 2 with real manual review~~ — done,
  `decisions.md` #54. Re-running at `min_votes=2` gave 107 candidates;
  read the actual note content (not just titles) for every structurally
  risky one and found 18 real errors (~17%) — `Windows`/`MS-DOS`/
  `Wininit.exe`/Mingw (contrasted-with-Linux, the same pattern #53 found),
  `GUI`→bash-scripting and `client-server model`→databases (wrong domain
  outright), `ultra-learning`→classical-ml (name collision with ML's
  "meta-learning," it's actually a study-technique note), `deep
  learning`→agents-llm (should be `deep-learning`, which exists, lost by
  one vote), and several too-generic notes (`Python objects`/`PYTHON
  ROADMAP`/`Python interpreter`/`programming language`/`interface`/
  `server`/`software application`/`USB flash drive`/`PCI devices`/`stock
  firmware`). The Python-related misses trace back to a real
  naming-scope issue: `agents-llm` absorbed general Python-tooling notes
  during #52's seeding, so it's broader in practice than its name
  suggests — flagged, not fixed. Applied the other 89.
  `DEFAULT_MIN_VOTES` stays 3; `--min-votes 2` is now documented as "use
  with a real manual review," not a safe default. Vault total: **1074 of
  1560 notes (68.8%) now carry a real domain**, up from 985 (63.1%).
- [x] ~~Second clustering pass over neighbor-vote's "stuck" notes~~ —
  done, `decisions.md` #55. Of 486 remaining unlabeled notes, 164 have
  real graph neighbors but none of them carry a domain either — the
  original `TCP` shape. Re-ran #52's clustering scoped to just those 164;
  found 17 real clusters (3+ members) out of 98 total. Presented each
  cluster's actual titles to the user per decision, not auto-approved by
  size: `python` (new, 5 notes — otherwise would've drifted into
  `agents-llm` later, same naming-scope problem #54 just flagged),
  `frontend` (new, 8 notes — React/Vite/CSS, kept separate from the
  existing `javascript` domain by user choice), `software-engineering`
  (new, 9 notes across 3 small meta clusters — Microservices/SDK/IDE/
  Software Quality), `personal-development` (new, 11 notes — the first
  non-technical domain in the system; two smaller non-technical clusters,
  dance and personal finance, 3 notes each, were explicitly left out).
  Two more clusters folded into existing domains without a separate
  question (unambiguous fit): Flynn Taxonomy/Mutex-semaphore-race-
  condition → `computer-architecture` (+6), X Window/compositor/Hyprland
  → `linux` (+3). Left alone: a 4-note cluster too ambiguous to name
  ("PLAN", "ENLARGEMENT"...) — not read, not guessed at; Unicode/encoding
  and a couple other small generic clusters, same reasoning as #51's
  exclusions. 42 applied total. Vault total: **1116 of 1560 (71.5%)**, up
  from 1074 (68.8%).
- [x] ~~Revisit `agents-llm` and `linux`'s scope~~ — done (decisions.md
  #56). Split `linux` (81) into `linux` (53) + new `operating-systems`
  (28: general OS/systems-programming fundamentals + other-OS-family
  notes); split `agents-llm` (36) into `agents-llm` (18) + new
  `knowledge-representation` (8: KG/ontology cluster) + existing `python`
  (+10 tooling notes, 5 → 15). 46 notes reassigned, existing `domain:`
  values overwritten (not a fill-in — bypassed `apply_classifications`'
  skip-if-labeled behavior via a one-off verified script).
- [ ] **Multiple domains per note** — surfaced in #52, not scoped.
  `domain:` as a vault frontmatter list is a small, additive parsing
  change; the real cost is everywhere `domain` is assumed to be a single
  `str` today (`MistakeEntry`, `SessionPlan`, `recommend_domain`'s
  rotation, the `tools.md` contract) — open questions like which
  domain's spaced-repetition clock a shared mistake should update aren't
  answered by the frontmatter change alone. Worth a real `decisions.md`
  entry of its own if/when a note genuinely needs it, not bundled into
  domain-inference work.
- [ ] **Taxonomy-aware classification** — surfaced by #56's rescoping.
  `build_class_centroids`/`classify_unlabeled_notes` treat every domain as
  a flat, independent class; #56 showed that's not why `linux` and
  `agents-llm` drifted broad — the embeddings scored fine, the *label*
  covered two or three genuinely different topics. Two directions worth
  trying once there's a second real case like this: (a) prepend a short
  domain description to the embedded text so classification sees intent,
  not just a bare name; (b) hierarchical classification — broad category
  first, then subdomain — which needs a real taxonomy structure defined
  first, not just flat domain names. Not scoped, no evidence yet beyond
  the one case.
- [x] ~~Phase 4: deprioritize `"general"` in `recommend_domain()`~~ —
  done, `decisions.md` #50, picked up ahead of phase 2 by explicit user
  choice (cheapest of the four, and the only one with real effect on
  today's data). `"general"` now only wins the automatic-mode rotation
  when it's the *only* domain with any tracked activity at all — verified
  against a copy of the real `mistakes.db`: a `"general"` mistake
  backdated 90 days (older than every real domain, enough to have won
  under the old rule) still loses to `languages`.

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
