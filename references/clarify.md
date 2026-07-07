# Clarify playbook (Recon, Clarify, Agree)

Purpose: turn a fuzzy request into a contractable objective with the fewest
questions that actually change scope, risk, or evaluation - and with zero
silent assumptions.

## Recon before questions

Run a quick, read-only pass before composing any question. Timebox it to
minutes. Gather:

- stack, entry points, and repo layout;
- build / test / eval commands (Makefile, package scripts, CI config);
- version pins and runtime environment;
- prior art: branches, TODOs, related issues or partial attempts;
- for ML repos: dataset location, configs, existing baselines or run logs.

Two outputs:

1. **Kill list** - questions the repo already answered. Never ask these;
   state them as findings.
2. **Grounding** - every question you do ask cites what recon found:
   "CI runs `pytest -q` on push; is exit 0 there the success criterion?"
   beats "how do I know it works?".

Deeper evidence (official docs via MCP, upstream issues, papers) happens
inside the Loop, following the evidence ladder in `loop-daor.md` - do not
stall the interview on it.

## Question discipline

- Format: 2-4 lettered options plus "or describe your own". Recommended
  option first, marked "(recommended)" with a one-line reason. Every option
  states its trade-off in one clause.
- Batching: up to 3 questions in one message when they are independent
  (no answer changes another question). Ask serially only when an answer
  would reshape what you ask next. At most 2 waves and 5 questions total.
- Required Codex wiring is installed during Setup and does not consume a
  question slot. Do not ask whether to install Stop hook or custom agents;
  SuperGoal assumes its trusted Codex environment.
- If the request already pins every dimension, ask zero questions and go
  straight to Agree with the assumption ledger.

## Skip test (run before every question)

Ask only if ALL three hold:

1. The answer changes what you would build, protect, or measure - the
   evidence genuinely supports two or more semantically distinct
   implementations, not cosmetic variants of one.
2. Recon could not answer it (and cannot within ~2 minutes) - further
   exploration would no longer narrow the options.
3. A wrong guess would be expensive to undo.

Navigational vs informational: a question whose answer lives in the repo
(which file, which command, which version) is navigational - recon answers
it, never the user. Ask the user only informational questions - intent,
business rules, hidden constraints, priorities - facts that exist only in
their head.

## Mandatory pins (may never stay implicit)

Loop engineering stands on verification and bounded iteration. Two answers
must be pinned before Agree, even when every other question is skipped:

1. **Success criterion** - the exact command, metric, and threshold that
   decide "done". Refuse a purely subjective criterion; negotiate a
   checkable proxy. Drill until objective: the command, the metric, the
   threshold, and the file or log the number is read from - e.g.
   "`pytest tests/ -q` exits 0", "val mIoU >= 0.78 in
   `runs/<id>/metrics.json`", "`npx playwright test` green and the deployed
   route returns 200 with the expected JSON shape via `curl`", or "crawler
   processes the 50-URL fixture list with >= 95% parse success and zero
   robots.txt violations in `crawl-report.json`". "Looks right in the
   browser" is the web-domain version of a subjective criterion - convert
   it to an e2e assertion or a measurable audit before Agree. This literal
   text becomes the verification surface and each PLAN.md `verify:` field.
2. **Iteration budget** - phrased for the user as "how long may I iterate
   before checking in with you": maximum DAOR cycles (default: 10, earlier
   if any stop rule fires; 5 when the tier check classified the mission
   high-risk - SKILL.md's Tier check owns that definition). ML adds
   GPU-hours and full-run caps.

Clarify's final message additionally ends with one non-question line naming
the tier and, for standard/high-risk missions, the estimated research scale
("standard tier; ~2 survey questions, roughly 60-100 sources") - the user
sees the spend coming before any research starts.

Pin each by asking, or - when clearly inferable - by writing the default
into the assumption ledger and having the user confirm it at Agree. Silent
defaults are forbidden for these two.

## Dimension checklist

Walk these five dimensions; ask only the ones that survive the skip test:

- **Aim** - success outcome and explicit non-goals.
- **Boundaries** - which code areas may change; dependency policy;
  wall-clock constraints; protected paths; checkpoint policy - whether the
  skill may make small green-state commits (default: no, journal notes
  only).
- **Context** - prior work to build on; reproduction steps; versions;
  runtime environment.
- **Done** - the mandatory success criterion above, plus any deliverable
  artifacts.
- **Evidence / Exit** - source of truth when results conflict (repo's own
  eval suite is the usual recommendation); the mandatory iteration budget.

## ML composite question (training / experiment tasks only)

Dataset, compute, and baseline are all mandatory for training tasks, but
they ship as ONE message so they never crowd out the other dimensions.
Present all three parts compactly; the user answers in one reply
(e.g. "1A 2B 3: paper number only"). Any part recon already pinned is
dropped and stated as a finding.

"Three quick ML facts - answer like '1A 2A 3B':

1. Dataset status
   - A. Ready; this repo's loaders already consume it (recommended if loaders exist)
   - B. Raw data present; needs analysis and preprocessing first
   - C. Needs downloading or collection - from where?
2. Compute budget
   - A. Smoke tests + up to 5 short proxy runs + up to 2 full training runs (recommended default)
   - B. A GPU-hours cap - how many hours?
   - C. No hard cap; I will still smoke-test before every full run
3. Baseline
   - A. Reproducible: config / checkpoint / metric exists - where? (recommended starting point)
   - B. Only a paper or README number; not yet reproduced locally
   - C. None; establishing one becomes the first subgoal"

## Scope-to-mission rule

If the goal is project-sized ("build me a recommendation system"), do not
plan the whole project as one mission. Carve out the first bounded mission -
the smallest outcome with a real success criterion that de-risks the rest -
propose it at Agree, and file the remainder as entries in
`.supergoal/BACKLOG.md` (`lifecycle.md`). One focused, falsifiable loop at a
time.

## Assumption ledger

Every dimension you did not ask about gets a written entry:

```markdown
- [low] Dependency policy: no new runtime deps (none present for this area).
- [low] Boundaries: changes stay under src/pipeline/ (task names only it).
- [low] Checkpoints: journal notes only; no commits by me unless you opt in.
- [HIGH] Data license permits redistribution -> must ask, do not assume.
```

Rules:

- Label each entry `[low]` or `[HIGH]` risk: how expensive is it to undo if
  the guess is wrong?
- A `[HIGH]` entry may not remain an assumption. Convert it into a question
  in the next wave (or the blocked-stop condition if the user is absent).
- `[low]` entries are presented at Agree for one-shot confirmation - the
  user corrects any line or says "go".
- The ledger is copied into `BRIEF.md`; a wrong confirmed assumption is a
  shared decision, a wrong silent assumption is your bug. On standard/high-risk
  (cluster) missions Clarify's outputs land in `.supergoal/DRAFT_BRIEF.md`
  instead, which feeds Research and Design and is promoted to `BRIEF.md` at
  Agree (`references/super-agent-cluster.md`).

## Agree message template

One message; the user replies "go" or corrects lines. This is the consent
checkpoint - never start the Loop before it is answered.

```markdown
## Objective
<one line, an end state, not an activity>

## Success criterion
<exact command / metric / threshold and where it is read from>

## Plan sketch
1. SG1 <outcome> - verify: `<command>`
2. SG2 ...          (riskiest first; ML: dataset + baseline first)

## Final design (standard/high-risk missions only)
<one-paragraph summary of DESIGN.md's accepted-version; the plan sketch above
is that design's subgoal plan, not a fresh guess>

## Boundaries
<allowed areas, protected paths, dependency policy, checkpoint policy>

## Assumptions (correct any line)
- [low] ...
- [low] ...

## Residual risks (standard/high-risk missions only)
- <accepted risks the final design inspection carried forward>

## Budget
<N DAOR cycles before check-in; ML: GPU-hours / full runs>

## If blocked
<what I will report and what input would unlock progress>

Reply "go" to start, or correct any line above.
```

The two design sections are present only on cluster missions, filled from the
inspected `DESIGN.md`; small missions omit them.

After "go", create the same content as one `/goal` command (`codex.md`).
`/goal` is the required mission contract layer for SuperGoal; if goals are
not enabled, stop and instruct the user to enable them before the Loop starts.

On cluster missions, "go" is also the promotion point - the exact crash-safe
order and the superseded-draft note live in
`references/super-agent-cluster.md`.

## BRIEF.md template

```markdown
# BRIEF

## Objective (EN)
## Non-goals
## Boundaries (files, deps policy, checkpoint policy)
## Context and prior work
## Success criterion (command / metric / threshold)
## Eval and source of truth
## Budgets (DAOR cycles / GPU-hours / full runs)
## ML status (dataset / baseline)          <- ML tasks only
## Recon findings                          <- Recon writes, Loop appends
## Assumption ledger (each [low] or [HIGH], confirmed at Agree)
```
