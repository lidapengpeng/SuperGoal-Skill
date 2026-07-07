# Super-agent cluster (standard/high-risk missions)

The runtime playbook for the 10-agent cluster. `SKILL.md` routes here after
Recon when the tiering test says a mission is not small. Small missions never
read this file - they run the pre-cluster path (`explorer`, `worker`,
`reviewer` only) exactly as `SKILL.md` defines it. This file is what the
skill reads at runtime; unverified platform assumptions and their deciding
measurements are tracked in `docs/field-validation.md`.

The cluster is a stronger *design harness* in front of DAOR. It changes
nothing behind Agree: once the design is inspected and the user says `go`, the
existing Loop / Gate / Close machinery runs unchanged.

## Tiering (which path a mission takes)

Reuse `SKILL.md`'s tier definitions, do not invent new ones (the small test
and the high-risk classifier both live canonically in SKILL.md's Tier check).
The small test already gates the plan-gate skip; this applies it one level
higher, to gate the cluster itself.

- **Small** -> pre-cluster path: Recon, Clarify, Agree, Loop, Close with the
  gates woven in (plan gate before cycle 1, subgoal gate per cycle, final gate
  before Close). `researcher`, `designer`, the four debate reviewers, and
  `synthesizer` never run. `reviewer` still gates every subgoal and the final
  claim - that was never optional.
- **Standard** -> full cluster: every wave W1-W8 below, minimum 1 debate
  round.
- **High-risk** -> full cluster with a minimum of 2 debate rounds (a
  plausible-looking draft must survive a second independent attack before
  code exists) and the shorter default budget leash from
  `references/clarify.md`.

The main thread applies the tests once, right after Recon, logs the decision
as a `## TIER` note in `JOURNAL.md` answering the criteria (so the
classification is auditable, not a silent judgment), and states the tier plus
the estimated research scale in Clarify's final message before any research
spend. This is a judgment recon mostly answers, not a question charged
against Clarify's budget.

**Mid-mission escalation.** If a "small" mission's real scope grows past the
test (discovered complexity, a subgoal that turns out to need an ML metric or
a non-deterministic verify), upgrade the tier without restarting. Because the
cluster agents' inputs must exist on disk first, escalation prepares them:
copy `BRIEF.md` to `DRAFT_BRIEF.md` (dated retro note at the top), have
`researcher` write a countersigned `## NO-WEB-RESEARCH` claims pack from the
evidence gathered so far (repo facts, journal observations), then run the
compressed design pass - one `designer` draft, one debate round with all four
reviewers, one inspection - before continuing DAOR. This mirrors the existing
scope-test / BACKLOG escalation in `references/loop-daor.md`; it is not a new
mechanism.

## Wave route

```text
Setup -> W1 Recon (explorer) -> tier check
  |
  |-- small ---------------> Clarify -> Agree -> Loop -> Close (pre-cluster)
  |
  \-- standard/high-risk --> W2 Clarify + Draft Brief    main thread + user
                          -> W3 Research + Claims        researcher
                          -> W4 Design Draft v1          designer
                          -> W5 Design Loop (1-3 rounds) design-reviewer | risk-reviewer |
                                                         verifier | leanness-reviewer
                                                         in parallel; on any REVISE:
                                                         synthesizer, then designer
                          -> W6 Final Design Inspection  reviewer (design mode)
                          -> Agree                       user replies "go" or corrects
                          -> Promotion + /goal           main thread
                          -> W7 DAOR Execution           main thread (+ worker)
                          -> W8 Completion Gates         reviewer (completion mode)
                          -> Close -> Next               main thread
```

W1-W6 are design-and-review; W7 is execution; the W8 subgoal gates plus the
final gate and the Stop hook are the checks. Within the standard/high-risk
branch the route is not further conditional on size - a mission with no
external facts still runs W3 through the NO-WEB-RESEARCH path, building the
claims pack from repo-local ground truth. Each wave's reads, durable output,
and return bound are pinned by its agent's role card (`config/*.toml`) plus
the work packet; ownership of every durable file is the table below.

## Durable state and the ID scheme

Files added for the cluster, all under `.dapeng/`:

| File | Content author | Disk writer | Purpose |
| --- | --- | --- | --- |
| `DRAFT_BRIEF.md` | main thread | main thread | Pre-Agree mission contract feeding research and design; promoted to `BRIEF.md` on `go`. |
| `RESEARCH.md` | `researcher` | `researcher` | Source register (contract, query log, one row per source) plus the distilled `## Claims` section (E-IDs, confidence, conflicts). |
| `DESIGN.md` | `designer` | `designer` (drafts), main thread (inspection block) | Versioned drafts, verification plan, final design inspection. |
| `DEBATE.md` | reviewers + `synthesizer` | main thread (verdict blocks), `synthesizer` (synthesis blocks) | Round-by-round objections, adjudications, gate decisions. |

Existing files keep their roles: `BRIEF.md` (user-approved contract),
`PLAN.md` (executable checklist), `JOURNAL.md` (DAOR evidence and completion
verdicts), `EXPERIMENTS.md` (ML run ledger).

The ID scheme is the cross-agent access mechanism: `Q<n>` research questions,
`S<nnn>` sources, `E<nnn>` claims, `DR/RR/VR/LR<round>.<n>` objections, `SG<n>`
subgoals. A work packet hands an agent file paths plus the ID ranges that
matter; the agent reads the files from disk (all sandboxes can read) and cites
IDs in its output. Nothing an agent produced exists for the cluster until it is
in one of these files.

At mission end these files archive with the mission
(`.dapeng/archive/<YYYYMMDD>-<slug>/`), exactly like BRIEF/PLAN/JOURNAL; a
pre-Agree parked mission archives `DRAFT_BRIEF.md` and whatever wave artifacts
exist.

## Research protocol (W3)

Answers the four questions every retrieval agent must have pinned: where to
search, in what time range, where findings are recorded, how other agents
access them.

### Two research modes (depth follows the objective)

Every research question is classified in the contract as one of two modes -
the mode decides where to search, how far back, and how deep. Base rules for
both: every question answered or gap-noted; every load-bearing claim on >=2
independent sources (or one official source plus corroboration); every source
dated (`date: unknown` never counts as current); timeless material (specs,
canonical papers) is tagged FOUNDATION and exempt from windows; claims
resting only on community sources (F4/F5 below) cap at `confidence: medium`;
padding the register with irrelevant sources is a defect in either mode.

**fix** (troubleshooting / problem solving - the deliverable is a working
fix candidate):

- Sources: the named tool's GitHub issues/PRs (F2), community threads (F4:
  HN, Reddit, X), Stack Overflow and practitioner posts (F5), general web -
  plus F1 docs/changelogs for version truth. The freshest community
  discussion often holds the real-world workaround.
- Window: newest first; default last 30 days, extended to whatever matches
  the pinned version.
- Depth: stop when the top 2-3 candidate fixes are each corroborated by >=2
  independent reports or one official acknowledgment - typically 5-15
  relevant sources per question. The decisive verification is DAOR actually
  running the fix; the register's job is ranked, cited candidates.

**survey** (state-of-the-art coverage - the deliverable is the approach
space, whatever the domain):

- Sources follow the question's domain, same coverage discipline either way.
  Academic questions (methods, models, algorithms): peer-reviewed venues
  first (F3: the CCF-A tier - e.g. CVPR, ICCV, ECCV, ICML, NeurIPS, ICLR,
  ACL - plus arXiv preprints), then F1 tech reports and F5 benchmarks,
  leaderboards, model cards. Engineering questions (framework/library/stack
  selection, architecture patterns - e.g. "which crawling stack"): F1
  official docs and release notes first, then F2 candidate repos
  (maintenance health), F5 benchmarks and migration reports; "approach
  families" become candidate stacks, and every candidate needs at least one
  F1/F2 source.
- Window: last 6-12 months for the frontier; FOUNDATION classics exempt.
- Depth: 30-60 relevant sources per survey question; fewer requires a logged
  gap note proving the space is smaller than that. Coverage is the point: a
  survey built on the first five hits is superficial by construction, so
  enumerate the distinct approach families first, then fill each family.
  This is the one place a depth floor survives the leanness rules - breadth
  IS the deliverable, and no qualitative sufficiency test catches an
  approach family that was never found.

A mission can mix modes per question. A pure version/API fact needs neither
mode - one official source answers it.

Per-mode source lists, windows, depth numbers, and confidence grading are
canonical in `config/researcher.toml` (the copy the agent is guaranteed to
load); the summaries above orient the scheduler and must not drift ahead of
the card.

**Call boundaries (multi-call research).** Call 1 writes the contract and
answers every fix-mode question; each survey question then gets its own
sequential call (or one call per approach family for very broad questions).
Every call appends `## Q<n> COMPLETE` when its question's collection and
claims are done, and every packet after the first carries the current highest
S-ID and E-ID so a resumed or subsequent call continues the sequence instead
of minting duplicates (`--audit` also scans for duplicate IDs). Sequential
calls, never a parallel fan-out.

### Query discipline (task deconstruction)

Before collecting, deconstruct each question into 3-8 planned query variants
(synonyms, method and tool names, error string + tool + version for fix
mode; venue-/arXiv-scoped or candidate-tool comparison searches for survey
mode, per the question's domain) and log them. During collection, log every
executed query with its hit quality, and refine low-precision queries
instead of accepting weak hits; the query log is what makes a gap note
checkable.

### Source families (where)

| Family | Sources | Authoritative for | Trust (evidence ladder) |
| --- | --- | --- | --- |
| F1 official | vendor docs, specs, RFCs, release notes, changelogs | API and version facts | ladder 2 - citable directly |
| F2 repos | GitHub issues, PRs, discussions, commits of the named tools | bugs, workarounds, roadmap | ladder 3 - citable with date |
| F3 papers | arXiv, ACL/NeurIPS/ICML proceedings, tech reports | methods, benchmarks | ladder 3 - usually FOUNDATION |
| F4 community-fast | Hacker News, Reddit (e.g. r/MachineLearning, r/LocalLLaMA, r/programming), X/Twitter engineering threads, Lobsters | current discourse, field reports | ladder 4 - corroborate before relying |
| F5 practitioner | engineering blogs, Stack Overflow, benchmark/leaderboard sites, Hugging Face forums and model cards, domain forums | how-tos, gotchas, comparisons | ladder 4 - corroborate before relying |

Every tool-specific question needs at least one F1 or F2 source; questions
about current practice should include F4.

### Contract, register, and claims (what gets recorded)

`researcher` writes the contract into `RESEARCH.md` before collecting:

```markdown
## RESEARCH CONTRACT <ISO-date>
- questions: Q1 <...> [fix]; Q2 <...> [survey]; ...
- timeframe: per mode defaults (fix: last 30 days; survey: last 6-12
  months) unless the user pinned a range at Clarify
- tooling: <web search / MCP servers actually available this session>
- sufficiency: fix -> top candidates corroborated by >=2 independent
  reports; survey -> 30-60 relevant sources per survey question or a
  logged gap note
- ceiling: <max sources and max executed queries for the whole wave -
  the T3 budget bound; exceeding it is a checkpoint, not a license>
```

Register rows, with a query log alongside (every search string and its hit
rate, so a gap note is checkable):

```markdown
| ID | Date | Family | Title | URL | Relevance | Freshness | Access | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S001 | 2026-07-02 | F4/HN | <title> | <url> | high | current | read | <one line> |
```

After collecting, `researcher` distills the register into the `## Claims`
section of the same file - testable claims, not source summaries:

```markdown
## Claims

### E001 (Q2)
- claim: <one testable claim>
- sources: S001, S014, S037
- confidence: high|medium|low
- freshness: current|foundation|stale
- conflicts: <none, or opposing S-IDs and status>
- usable-for-design: yes|no
```

Confidence grading: high needs 3+ independent current sources or one official
source plus corroboration; medium needs 2; low is a single source and must say
so. Conflicts are marked with the opposing S-IDs, never averaged away.

For survey questions the claims enumerate the approach space: one claim per
approach family (its representative S-IDs, reported benchmark numbers where
they exist), plus explicit gap claims for what the literature does not yet
answer - this is the methodology synthesis the designer consumes.

If neither web search nor an MCP server is available, `researcher` writes a
`RESEARCH BLOCKED` note and the main thread raises a user checkpoint with the
two options named: proceed repo-only (via the NO-WEB-RESEARCH path) or halt
until tooling exists. When the mission needs no external facts, `researcher`
writes a dated `## NO-WEB-RESEARCH` note justifying why repo-local ground
truth suffices, the main thread countersigns it with a dated line (a logged
decision, not a subagent's self-declaration), and the claims pack is built
from repo-local evidence with `Family: repo` S-IDs whose URL is a repo path.

Register integrity: before design consumes the claims, the main thread (which
has web access when the researcher did) spot-fetches 2-3 randomly chosen
S-IDs and confirms the row describes the source - offline debate reviewers
cannot do this, so it is the scheduler's duty.

### Access (how other agents use it)

Downstream packets name the files and the relevant ID ranges - never pasted
bulk content. Agents read `RESEARCH.md` from disk and cite S-IDs / E-IDs in
every factual statement. The main thread rejects any design or debate output
whose load-bearing claims lack citations.

## Work-packet contract (flexible prompts)

Every agent invocation is built from the same packet shape, generated by the
main thread from current disk state:

```markdown
- mission: <slug>
- wave: <name, round if any>
- task: <one paragraph, the charter for this call>
- inputs: <file paths + ID ranges + at most ~30 lines of excerpts>
- output: <exact file and section to write, or "return only">
- limits: <return-line bound, timeframe>
- forbidden: <out-of-scope actions for this call>
```

Debate packets additionally carry: the allegation ("this design is
implementation-ready") framed as a claim to attack, the reviewer's charter, the
previous rounds' `least-examined:` lines, and never the main thread's own
opinion of the design - a persuaded reviewer is a broken reviewer.

## Scheduler duties (main thread)

- Choose the next wave; construct packets; enforce return bounds.
- Write `DRAFT_BRIEF.md`, all `DEBATE.md` verdict blocks and gate decisions,
  the `DESIGN.md` inspection block, and all of `BRIEF/PLAN/JOURNAL/EXPERIMENTS`.
- Reject agent output that lacks citations or violates its packet; a rejected
  output is re-run with the defect named, not patched by the scheduler. Every
  rejection is a dated line in `DEBATE.md` - an unlogged rejection is
  indistinguishable from acceptance.
- Research orchestration per the call-boundary rules above (call 1 covers
  the contract and fix questions; one sequential call per survey question;
  ID maxima in every follow-up packet).
- Snapshot the write-audit baseline immediately before EACH write-capable
  agent spawn (not once per wave): run
  `python <repo>/.codex/hooks/subagent_audit.py --snapshot`, which records a
  content hash of every `.dapeng/` file (tmp/ and archive/ excluded) into
  `.dapeng/tmp/.write-audit-baseline`. Between that snapshot and the agent's
  turn end the scheduler writes nothing under `.dapeng/` - otherwise its own
  writes are attributed to the agent. In parallel mode the baseline is not
  advanced between overlapping turns. The `SubagentStop` hook performs the
  check on turn end; it is experimental (designed from Codex hook docs, not
  verified against a live install), so until verified, run
  `python <repo>/.codex/hooks/subagent_audit.py --audit <agent>` after each
  write-capable turn as the primary safety net - same snapshot, same
  allow-lists, plus a duplicate S/E-ID scan; exit 1 with the violation list
  on a breach. Known honest limit: the audit is file-granular - an agent that
  owns a file can rewrite that file's history undetected; the final
  inspection and completion gates re-derive from content, which is the
  compensating control.
- Decide `GO | REVISE | BLOCK` at every gate; agents only recommend.
- Keep one active `/goal` and one active `PLAN.md`.
- Never paste full agent transcripts into later packets; pass paths and IDs.

## Design loop (W5): design -> review -> redesign

Minimum 1 round (standard) or 2 rounds (high-risk), maximum 3 per burst. The
independent confirmation of an all-GO round on a standard mission is the W6
final inspection by a reviewer who never saw the debate; on a high-risk
mission a plausible draft must additionally survive a second debate round
seeded by round 1's `least-examined:` lines before code exists.

```text
r = 1; min_r = 1 (standard) or 2 (high-risk); total = 0
loop:
  1. Debate: design-reviewer, risk-reviewer, verifier, leanness-reviewer
     run in parallel, isolated - none sees the others' current-round
     output. The main thread writes all four verdict blocks into DEBATE.md
     only after all four have returned. total += 1.
  2. Gate decision (mechanical):
     - any BLOCK               -> user checkpoint; loop suspends.
     - all GO and r >= min_r   -> exit loop to W6.
     - all GO and r <  min_r   -> confirmation round: skip synthesis and
                                  redesign; reviewers re-attack the SAME
                                  draft seeded by this round's
                                  least-examined lines; r += 1.
     - any REVISE, r == 3      -> user checkpoint: unresolved objections
                                  plus options (relax scope, accept a named
                                  risk explicitly, or supply missing
                                  input). No fourth redesign first.
     - any REVISE, r < 3       -> continue to synthesis.
  3. Synthesis: synthesizer adjudicates and appends its section.
  4. Redesign: designer produces DESIGN DRAFT v<next> applying accepted
     objections.
  5. r += 1.
```

Rules:

- Maximum 3 rounds per unattended burst: a design that cannot converge in 3
  rounds has a problem no fourth round will fix; it goes to the user.
- `synthesizer` and redesign run only when a round contains REVISE - a
  unanimous round costs nothing beyond the four reviewer calls.
- After a user checkpoint (BLOCK or round-3 failure), the round counter
  resets ONLY when the reply materially changed the brief or the design
  constraints (new input, relaxed scope, an accepted named risk); a bare
  "continue" does not reset it. Hard cap: 6 debate rounds total per mission
  regardless of resets - reaching it is a stop, not a license (T3).
- Root-objection rule: the same root tag accepted in two consecutive rounds
  forbids a third patch - the affected design area is re-derived from first
  principles (pre-implementation analog of hard rule 4).
- Reviewers see previous rounds (DEBATE.md on disk) but never the current
  round: the main thread transcribes verdicts only after all four return,
  and packets carry excerpts of prior rounds - never an instruction to read
  the current round live. Reviewers end their return with a single verbatim
  verdict line, which the main thread transcribes unchanged; the W6
  inspector re-derives from the full trail, which is what catches a softened
  transcription. Each reviewer ends with a `least-examined:` line; later
  rounds' packets carry those lines so the next round probes what the last
  one skipped.
- An all-GO exit's minor objections do not evaporate: the main thread copies
  them into the W6 inspection packet as mandatory disposition items.

### DEBATE.md round format

```markdown
## DEBATE R<r> <ISO-date>
### design-review
- verdict: GO|REVISE|BLOCK - <one line>
- objections:
  - DR<r>.1 [major] [root: <slug>] <claim> | evidence: <IDs or
    file:line> | required-change: <one line>
- least-examined: <areas>
### risk-review
(same shape, RR<r>.n; add `- alternative: RR<r>.ALT -> <<=20-line sketch>`
only when the alternative-solution duty fires on a major objection)
### verifier-review
(same shape, VR<r>.n)
### leanness-review
(same shape, LR<r>.n; each objection names the systemic fix)
### gate decision (main thread)
- round-result: GO|REVISE|BLOCK - <one line>
```

On a REVISE round the synthesizer then appends its own top-level section -
append-only, like every other write in the system; it never edits inside the
round block it adjudicates:

```markdown
## SYNTHESIS R<r> <ISO-date>
- accepted: DR<r>.1 -> <redesign instruction>; ...
- rejected: RR<r>.2 -> <stated reason>; ...
- alternative: RR<r>.ALT -> accepted (redesign around it) | rejected
  (<stated reason the existing approach still wins>)
- escalated: <IDs needing the user>
- carried: <unresolved minor IDs>
- root-tags: <every prior accepted root tag with an explicit
  match/no-match against this round's objections - the synthesizer is
  the sole tag authority, so a renamed slug cannot dodge recurrence>
- recurring-roots: <tags matched in 2+ rounds, first-principles trigger>
- gate-recommendation: GO|REVISE|BLOCK - <one line>
```

### DESIGN.md draft skeleton

```markdown
## DESIGN DRAFT v<n> <ISO-date>
### Problem and goals
### Non-goals
### Chosen approach            (cites E-IDs / file:line)
### Rejected alternatives      (each with the reason)
### Components and interfaces
### State and data flow
### Error and edge handling
### Subgoal plan               (SG list: outcome | verify | done-when)
### Verification plan          (Observe-0 baseline, metrics, stop
                                conditions, anti-gaming guards)
### Risks and mitigations
### Open questions
### Changes from v<n-1>        (v2+: objection IDs addressed)
```

### Final design inspection (W6)

After loop exit, `reviewer` (design mode, fresh context, no debate
participation) audits the accepted draft. The main thread writes the block at
the end of `DESIGN.md`:

```markdown
## FINAL DESIGN INSPECTION <ISO-date>
- accepted-version: v<n>
- design-final: GO|REVISE|BLOCK - <one line>
- implementation-ready: yes|no
- residual-risks: <accepted risks carried into BRIEF.md>
```

A `REVISE` here routes straight to the designer with the inspection text as
its redesign instructions (no synthesis step - the inspector's findings are
already adjudicated by being the fresh-eyes verdict), then one re-inspection;
if still not `GO`, it becomes a user checkpoint. A re-inspection APPENDS a
new dated `## FINAL DESIGN INSPECTION` block; the latest block is
authoritative (the Stop hook reads the last one). No design marker anywhere
may use the string `review: PASS`.

## Interaction with existing DAOR (behind Agree)

1. Agree presents: objective, success criterion, final design summary with
   `accepted-version`, subgoal sketch, assumption ledger, residual risks,
   budget, blocked-stop condition. The user replies `go` or corrects lines;
   any other reply (a question, "go but also X", refusal) is continued
   Clarify - scope additions route through the scope test, and nothing
   promotes until a clean `go` or corrected-lines reply.
2. On `go`: promotion runs in crash-safe order - `PLAN.md` is derived
   mechanically from the accepted draft's subgoal plan and written FIRST
   (it is re-derivable), then `DRAFT_BRIEF.md` is COPIED to `BRIEF.md` with
   user corrections applied, then a dated `> promoted: superseded by
   BRIEF.md` note is prepended to `DRAFT_BRIEF.md`, then the one top-level
   `/goal` is created. From this point every packet references `BRIEF.md`,
   never the superseded draft (including reopen debate rounds). If a user
   correction touched a subgoal line, append a dated design amendment note
   to `DESIGN.md` recording the divergence from the accepted draft.
3. Plan gate: when the user replied `go` unchanged, log `plan-review: SKIPPED
   (covered by design gates R1-R<n> and final inspection)`; when the user
   corrected any contract line, run the plan gate on the corrected contract
   before cycle 1. Either way the `## PLAN GATE` section quotes the user's
   Agree reply verbatim, so the skip condition is auditable. The marker
   spelling stays `plan-review:`, never `review: PASS`.
4. DAOR executes one subgoal per cycle; `worker` is optional per its role
   card; `reviewer` (completion mode) gates every subgoal and the final
   claim, and its checklist includes the leanness dimension (file count,
   patchwork, dead code, `ponytail:` comments) - there is no separate
   execution-time leanness call.
5. Reopen (defect against the closed mission's success criterion): append a
   dated `## REOPEN DESIGN NOTE` to `DESIGN.md` stating whether the defect
   invalidates the accepted design. If yes, run one debate round (all four
   reviewers) on the amended design before the fix cycle; if no, record the
   reason and proceed.

The Stop hook gains one check: when `PLAN.md` exists (the mission passed
Agree) *and* `DESIGN.md` exists (the mission is a cluster mission), `DESIGN.md`
must contain a `## FINAL DESIGN INSPECTION` section with
`implementation-ready: yes`, otherwise Close is blocked. Small missions never
create `DESIGN.md`, so the check cannot fire for them; sessions ending
pre-Agree (no `PLAN.md`) are not blocked by it either. Design gates are never
treated as completion evidence.

## Resume semantics

Every wave boundary is recoverable from disk; no chat memory is consulted.
Presence checks include a minimal shape check - a stub file does not count
(RESEARCH.md needs its contract section and at least one claim block before
it certifies W3 as done). On re-invocation with an open pre-Agree mission the
router infers position:

- `DRAFT_BRIEF.md` present but no well-formed `RESEARCH.md` -> resume at W3
  (a partial register resumes at its first question without a
  `## Q<n> COMPLETE` marker, packet carrying the current S/E-ID maxima).
- `RESEARCH.md` well-formed but no `DESIGN.md` -> resume at W4.
- The last `## DEBATE R<r>` block and its gate decision tell whether the loop
  exited. A round block with no `gate decision` line is VOID: the crash hit
  mid-round; rerun all four reviewers with a packet instruction to ignore the
  incomplete block (this preserves in-round isolation).
- An inspection whose latest block is not `implementation-ready: yes` ->
  resume at the targeted redesign step.
- Latest inspection `yes` but no `BRIEF.md` -> resume at Agree.
- `BRIEF.md` present but no `PLAN.md` -> the promotion crashed mid-write;
  re-derive `PLAN.md` from the accepted draft's subgoal plan (the Stop hook
  also blocks on this state).

**Pre-Agree park.** When urgent work supersedes a mission that has not
reached Agree, the post-Agree park procedure in `references/lifecycle.md`
does not apply (no PLAN.md or JOURNAL.md exists). Instead: prepend a dated
`> PARKED: superseded by <slug>` note to `DRAFT_BRIEF.md`, archive
`DRAFT_BRIEF.md` and whatever wave artifacts exist to
`.dapeng/archive/<YYYYMMDD>-<slug>-PARKED/`, and delete the write-audit
baseline. Resuming restores the files and re-enters at the inferred wave.

## Migration (existing missions)

A repo with an open pre-cluster mission either finishes it under the old
semantics before the cluster is exercised, or adds this dated retro note to a
new `.dapeng/DESIGN.md` - verbatim, because the Stop hook string-matches the
marker:

```markdown
## FINAL DESIGN INSPECTION <ISO-date>
- design-final: GO - retro note: mission predates design gates
- implementation-ready: yes
- residual-risks: design was never cluster-reviewed (pre-cluster mission)
```

A mission whose `.dapeng/` predates this playbook revision and still has an
`EVIDENCE.md` finishes with it; new missions write claims into
`RESEARCH.md ## Claims`.
