# Clarify playbook (Recon, Clarify, Agree)

Purpose: turn a fuzzy request into a bounded, verifiable mission with the
fewest questions that actually change scope, risk, or evaluation. Do not make
the user answer questions the repository can answer.

## Recon before questions

Run a short read-only pass before composing any question. Timebox it to
minutes. Gather:

- stack, entry points, and repository layout;
- build, test, evaluation, and CI commands;
- version pins and runtime environment;
- related code, TODOs, branches, issues, and partial attempts;
- protected paths, generated files, lockfiles, and shared surfaces;
- for ML: dataset location, configuration, baselines, and run logs.

Produce two things:

1. **Kill list:** questions recon already answered. State these as findings;
   never ask them.
2. **Grounding:** every remaining question cites what recon found. For
   example, "CI runs `pytest -q`; is exit 0 there the success criterion?" is
   better than "How do I know it works?"

External research belongs after Agree and only if uncertainty changes a
technical choice, safety decision, or dependency edge. Do not turn intake
into an automatic research fan-out.

## Question discipline

- Offer two to four lettered choices plus "describe your own". Put the
  recommended choice first and say its trade-off in one sentence.
- Ask up to three independent questions at once, up to two waves and five
  total questions. Ask serially only when an answer changes the next question.
- A precise request gets no invented questions: state safe defaults in the
  assumption ledger and request one confirmation at Agree.
- Required SuperGoal wiring is not a product question. Install or report a
  collision during Setup; never ask the user to choose an internal role card.

## Skip test

Ask a question only when all of these hold:

1. Its answer changes what would be built, protected, measured, or delegated.
2. Recon cannot answer it quickly.
3. A wrong guess would be expensive to undo.

Questions answered by the repository are navigational, not informational.
Ask the user about intent, hidden constraints, business priorities, and
authority—not paths, versions, or commands that can be observed.

## Mandatory pins

The following must be explicit before Agree:

1. **Success criterion:** exact command, metric, threshold, and where the
   result is read. Convert "looks right" into a measurable proxy or an e2e
   assertion. Examples: `pytest tests/ -q` exits 0; a metric in a named JSON
   file reaches a threshold; a crawler processes a fixed fixture with a known
   success rate and no policy violations.
2. **Budget:** maximum DAOR cycles, wall-clock/research allowance, and maximum
   direct task records (0–10 total, including optional research), plus for ML
   GPU-hours and full-run caps. The budget is a ceiling, not an instruction to
   use every task slot.

Ask these directly or put a clearly inferred default in the assumption ledger
for the user to confirm. Never hide worker cost inside a generic “research”
line.

## Dimension checklist

Ask only dimensions that survive the skip test:

- **Aim:** desired outcome and explicit non-goals.
- **Boundaries:** allowed code areas, dependency policy, protected paths,
  external side effects, worktree policy, and checkpoint policy.
- **Context:** prior work, reproduction steps, versions, and runtime.
- **Done:** success criterion and required deliverables.
- **Evidence / exit:** authoritative source of truth, budget, blocked-stop
  behavior, and whether external facts could change the plan.

## ML composite question

For training or experiment work, ask dataset, compute, and baseline together
in one compact message. Drop parts recon already pinned.

```text
Three ML facts — answer like “1A 2A 3B”:

1. Dataset: A. ready in this repo (recommended) | B. raw/preprocessing needed |
   C. needs collection, specify source
2. Compute: A. smoke + bounded proxy/full runs (recommended) | B. GPU-hour cap |
   C. no hard cap, still smoke-test first
3. Baseline: A. reproducible config/checkpoint/metric (recommended) |
   B. paper/README only | C. none; baseline becomes the first plan node
```

## Scope-to-mission rule

If the request is project-sized, carve out the smallest outcome that can be
verified and meaningfully de-risks the rest. Put the remainder in
`.supergoal/BACKLOG.md`. One DAG should describe one bounded mission, not an
aspirational roadmap.

## Assumption ledger

Every dimension not asked becomes an explicit, risk-labelled assumption:

```markdown
- [low] Dependency policy: no new runtime dependency unless the plan review finds it necessary.
- [low] Boundaries: implementation stays under src/pipeline/ and its tests.
- [low] Checkpoints: journal notes only; no commits unless the user opts in.
- [HIGH] Data license permits redistribution -> ask; do not assume.
```

High-risk assumptions may not remain assumptions. Turn them into a question,
a dependency that blocks execution, or a user checkpoint.

## Agree message template

Send one message. The user replies `go` or corrects a line; any scope addition
returns to Clarify.

```markdown
## Objective
<one end state, not an activity>

## Success criterion
<exact command / metric / threshold and source of truth>

## Provisional plan
1. <outcome or investigation> — verify: `<command or evidence condition>`
2. <dependent outcome> — verify: `<command>`
<The controller will validate the executable DAG after approval.>

## Risk and execution policy
- tier: <small|standard|high-risk + reason>
- research: <not needed | bounded question(s) and why uncertainty matters>
- delegation: up to <0–10> direct task records total; research counts; no filler work
- integration: controller-owned worktree and full verification after merge

## Boundaries
<allowed paths, protected paths, dependency and checkpoint policy>

## Assumptions (correct any line)
- [low] ...

## Budget
<DAOR cycles, wall-clock, research allowance, maximum direct task-record count;
ML GPU-hours/full runs if applicable>

## If blocked
<what will be reported and what input unlocks it>

Reply "go" to start, or correct any line above.
```

One `go` approves the contract and its maximum spend. It does not pre-approve
an unreviewed DAG, a destructive action, or a worker count that has no
independent work to justify it.

On `go`, the controller writes `PLAN.md`, `BRIEF.md`, and a plan-phase
`run_manifest.json`, then creates one `/goal`. The manifest stores machine
state; `BRIEF.md` stores the human-approved contract.

## BRIEF.md template

```markdown
# BRIEF

## Objective (EN)
## Non-goals
## Boundaries (allowed/protected paths, dependencies, checkpoint policy)
## Context and prior work
## Success criterion (command / metric / threshold)
## Eval and source of truth
## Budget (DAOR / research / 0–10 total task-record ceiling / wall-clock / ML limits)
## ML status (dataset / baseline)          <- ML tasks only
## Recon findings
## Assumption ledger (each [low] or [HIGH], confirmed at Agree)
```
