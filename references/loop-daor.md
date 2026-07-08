# DAOR loop discipline (Loop phase)

One cycle = one controlled experiment. Never "change something and see".
The Agree contract gives the global stop condition; DAOR gives the per-cycle
discipline.

## Observe-0 (once per task, before any change)

- Run the agreed eval on the untouched state; record the baseline number,
  exit codes, and any pre-existing failures. Greenfield work has one too:
  the failing or absent result IS the baseline - record it.
- Record the environment: commit hash, seed policy, dataset version,
  hardware. Without a baseline, "improvement" is unfalsifiable.

## The four phases

Naming: the cluster **design phase** (D1-D4 in `references/super-agent-cluster.md`)
runs once after Agree on standard/high-risk missions and produces DESIGN.md.
Each DAOR cycle's **Design** step below is a per-cycle falsifiable hypothesis
for one subgoal - it does not reopen D1-D4. Mid-loop redesign of the accepted
design is a separate path (hard re-Agree if the contract shape moves).

### 1. Design (per-cycle hypothesis)

- If `.supergoal/PROJECT.md` exists, check its `L-` lessons for the problem at
  hand before hypothesizing: an approach this project already refuted is
  context, not a candidate. The file is capped, so this costs one read.
- Hypothesis in one sentence: "the bottleneck is X; changing Y should move
  metric Z by roughly dZ".
- Exactly one variable. If two things must change together, that is one
  composite variable - say so and plan the ablation that separates them later.
- Write the verify command, the expected result, and the failure criterion
  (what observation would refute the hypothesis).
- Falsifiability gate: if no possible observation could refute it, redesign
  the experiment before acting.

### 2. Act

- Make the smallest defensible change that implements the design. No
  unrelated refactors, no drive-by cleanups, no new dependencies unless the
  design says so.
- ML: smoke-test first - tiny subset, few steps, reduced resolution; assert
  the pipeline runs, loss moves, shapes and IO are sane. Only then spend the
  budget on a full run. Record checkpoint paths and the resume command.

### 3. Observe

- Read actual outputs only: test results, training and eval logs, metric
  files, sample artifacts, profiler output.
- Quote raw numbers and log lines into the ledger. Paraphrasing from memory
  is forbidden; "it seems better" is not an observation.
- Trust artifacts, not narration: exit codes, diffs, files, logs that can be
  re-run. A model's or platform's self-description - displayed "thinking"
  text, subagent summaries, "I have verified..." - is never verification
  evidence.
- Long runs: check intermediate signals (loss curve, LR schedule, grad norms)
  before waiting for completion; kill clearly diverged runs early and record
  the kill as an observation.

### 4. Reason

- Compare expected vs actual. Verdict: supported / refuted / inconclusive.
- Attribute: what does this imply about the current bottleneck model?
- Decide: continue this line, pivot to a new hypothesis, or trigger a stop
  rule. Name the root cause every time a failure repeats - root-cause
  tracking feeds hard rule 4: two failed patches on the same root cause is
  itself a stop rule (pause for a user checkpoint), and by the time you
  raise it you should have already re-derived from first principles
  (re-read the paper/docs/source, re-model the design in BRIEF.md) so the
  checkpoint offers a diagnosis and a proposed redesign for the user to
  confirm, not just a report that patching failed.
- A refuted expectation or a gamed check becomes a permanent guard: fold the
  counterexample into that subgoal's verify command so the same failure can
  never pass silently again. It also becomes memory: record or update the
  root's `L-` entry in `.supergoal/PROJECT.md` (rules in
  `references/lifecycle.md`) - immediately when hard rule 4 fires (the
  checkpoint's diagnosis is the entry), at Close's consolidation sweep for
  everything else.

## JOURNAL.md entry format (append-only, one per cycle)

```markdown
## C<n> <ISO-date> SG<id>
- design: <hypothesis; single variable; verify cmd; expected result>
- act: <files changed / run id / smoke result>
- observe: <quoted metrics, log lines, exit codes>
- reason: <supported|refuted|inconclusive; root cause; next step>
- review: <PASS|FAIL|CANNOT-VERIFY + one line>   <- only when a gate ran
```

The plan gate (when the tier requires it) is logged before C1 - note the
distinct field name; `review: PASS` is reserved for completion evidence:

```markdown
## PLAN GATE <ISO-date>
- plan-review: GO - <one line>        (or REVISE - <objection> / SKIPPED (small mission) - <one line>)
```

The final gate gets its own section when it passes:

```markdown
## FINAL GATE <ISO-date>
- review: PASS - <one line>
```

These are machine-checked markers, keep the exact spelling: the Stop hook
cross-checks every checked PLAN.md box against a journal section whose
HEADER line names its `SG<id>` and whose body logs `review: PASS` (FINAL
against the `## FINAL GATE` section). Body mentions do not count. Drift
from this format and the hook will refuse to let the session end.

## Standard/high-risk missions: design provenance and the leanness gate

On standard/high-risk missions the implementation cycles do not invent the
design cycle by cycle. The Loop OPENS with the design phase
(`references/super-agent-cluster.md`): the approach, subgoal plan, and
verification plan are authored, debated, and inspected under the contract's
design budget, live in `.supergoal/DESIGN.md`, and the implementation
subgoals in `PLAN.md` are derived from that accepted design. DAOR then runs
one falsifiable cycle per subgoal - it executes the inspected plan, it does
not re-open it. A genuinely new subgoal discovered mid-mission still passes
the scope test below before it is added.

Execution-time leanness is part of the `reviewer` completion gate, not a
separate call: the reviewer's code dimension includes file-count creep,
patchwork, dead code left behind, and missing `ponytail:` comments, so a
bloated diff FAILs its subgoal gate like any other defect and goes back to
Act. (`leanness-reviewer` itself runs only inside the design debate.)

## Checkpoint on green

After a cycle's verify passes and its review verdict is logged, checkpoint
the state: a small single-purpose `git commit` only if the user opted in at
Agree (checkpoint policy in the boundaries), otherwise a JOURNAL.md note
naming the exact green state - files touched and the verify output. When a
later cycle wrecks the working tree, restore the last green checkpoint and
redesign - never forward-fix a broken state you cannot reason about.

## Triple stop control

1. **Iteration cap** - from the Agree contract (default: 10 cycles per
   mission; revisit the plan with the user if you hit it).
2. **No-progress detection** - three consecutive cycles without metric or
   test improvement, or the same root cause failing twice: pause and
   checkpoint with the user. This is the most important control.
3. **Budget ceiling** - GPU-hours / full-run count / wall-clock from the
   contract. Exhausted budget = stop and report, never "one more quick run".

Also stop immediately for: protected paths, destructive or irreversible
actions, unreliable evals (flaky tests, non-deterministic metric without a
seed policy), and any product/security/privacy/billing decision.

## Evidence ladder (Recon and throughout the Loop)

1. Repo source, tests, fixtures, CI config, logs.
2. Official docs, specs, API references - via MCP servers or web.
3. Upstream changelogs, issues, PRs, papers.
4. Reputable community discussion (weak signal, corroborate before relying).
5. Model memory - never sufficient alone for version-sensitive facts.

Rules: any version-sensitive fact must be verified at level 1-3 before code
depends on it. MCP first: Setup's tooling inventory says what exists - a
configured docs/knowledge server (e.g. deepwiki, context7) is the preferred
level 2-3 source, and a semantic code-navigation server (e.g. serena) beats
raw grep at level 1; never fabricate MCP access. Uncertain + high-risk next
step: ask the user now. Uncertain + low-risk: proceed with a labeled
conservative assumption.

## Context hygiene

The main thread is a scheduler: keep its context for decisions. Push bulk
work down - long log parsing, wide code searches, big builds - to subagents
or to files under `.supergoal/tmp/`, and pull back only the distilled result.
On long missions prefer starting a fresh context at a cycle boundary over
compacting a bloated one - BRIEF.md + PLAN.md + the JOURNAL tail are the
entire handoff, by design. After any reset or compaction, re-read them
before the next cycle; disk state is the memory, not the chat.
