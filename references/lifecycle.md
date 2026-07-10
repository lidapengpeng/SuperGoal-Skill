# Project lifecycle (Next)

The mission layer finishes one bounded outcome. The project layer preserves
what should influence the next one. Keep them separate:

- **Mission layer:** one active `BRIEF.md`, `PLAN.md`, `JOURNAL.md`,
  `run_manifest.json`, one `/goal`, and a final review.
- **Project layer:** backlog, concise standing facts, and archived missions.
  These inform judgment but do not masquerade as completion evidence.

```text
BACKLOG idea
  -> compact intake / Agree
  -> plan DAG + optional research + plan review
  -> 0..10 independent task records, integration, full verification
  -> fresh final review
  -> archive
  -> next mission / reopen / backlog
```

## When Next runs

Reach Next only after the current manifest has `phase: "complete"`, all tasks
are accepted as `complete` or `skipped` and accounted for, integration is complete, final verification
passes, and a fresh `supergoal_reviewer` PASS is recorded. `PLAN.md` and
`JOURNAL.md` must tell the same human story. A completion-audit hook can catch
an inconsistent state, but it does not replace these checks.

## Classifying new work

Every incoming idea has one home:

1. **New mission:** new outcome, success criterion, or budget. This is the
   default when uncertain.
2. **Reopen:** defect, missing evidence, or regression against the previous
   mission's stated success criterion.
3. **Backlog:** real idea not ready for a committed outcome/budget.

**Park** is a separate transition for an open mission displaced by urgent
work; it is not a completion claim.

## New mission

1. Archive completed root files, including `run_manifest.json`, any
   `RESEARCH.md`, and `EXPERIMENTS.md` when present.
2. Create a fresh Codex thread where practical; one active goal per thread
   keeps state and verification clear. `/goal clear` is a fallback only when
   staying in the thread is necessary.
3. Start compact Clarify pre-filled from `PROJECT.md`. Re-ask only the success
   criterion and budget when they are not already safely inferable; present
   other defaults as assumptions for Agree.
4. On Agree, create new `PLAN.md`, `BRIEF.md`, `JOURNAL.md`, and a plan-phase
   manifest. Do not copy a completed task or stale base SHA into the new run.

## Reopen

1. Append `## REOPEN <ISO-datetime>` to `JOURNAL.md` with the defect, violated
   success criterion, current SHA, and evidence.
2. Add a new unchecked plan item before `FINAL` and uncheck `FINAL`.
3. Change the manifest back to `phase: "plan"`, update `base_sha`, set
   integration to pending, and build/review a fresh DAG for the remaining
   work. Old terminal tasks are historical evidence, not automatic approval
   for a changed snapshot.
4. Run DAOR, integrate, verify, and final-review again. A later PASS must
   cover the reopened state.

## Backlog

Record future work in `.supergoal/BACKLOG.md` and touch no executable state.
Backlog entries have no checkbox because a casual idea must not block a
mission's close:

```markdown
## Idea <ISO-date> - <short title>

- status: candidate
- source: <where it came from>
- possible outcome:
- possible verification:
- risks:
- promote-when:
```

## Park

When urgent work arrives before close:

1. Mark remaining plan items as parked with the input required to resume.
2. Append a `## PARK <ISO-date>` journal entry: completed work, remaining
   nodes, base SHA, and resume condition.
3. Archive the whole mission state under a `-PARKED` folder; do not mark it
   complete.
4. Start intake for the urgent mission.

On resume, restore the files and revalidate the manifest. Any planned/running
task based on an old SHA is stale and must be rebased or replanned before
execution. Preserve completed evidence, but re-run final verification after a
meaningful workspace change.

## Archive layout

```text
.supergoal/
  BACKLOG.md
  PROJECT.md
  BRIEF.md              # active mission only
  PLAN.md               # active mission only
  JOURNAL.md            # active mission only
  run_manifest.json     # active mission only; machine-readable contract
  RESEARCH.md           # optional
  EXPERIMENTS.md        # optional
  tmp/
  archive/
    20260709-ci-speedup/
      BRIEF.md
      PLAN.md
      JOURNAL.md
      run_manifest.json
      FINAL-REPORT.md
    20260710-data-migration-PARKED/
      BRIEF.md
      PLAN.md
      JOURNAL.md
      run_manifest.json
```

Folder names are `<YYYYMMDD>-<slug>`; append `-PARKED` when appropriate. One
active mission per root state prevents stale subgoal IDs, reviewer verdicts,
and base SHAs from being confused with the next mission.

## PROJECT.md

Keep this as thin operational memory, not a transcript. Read it at intake and
before a DAOR Design step; keep it under roughly 150 lines and prune facts the
repository itself already supplies.

```markdown
# PROJECT

## Standing defaults
- eval command:
- default DAOR budget:
- default direct task-record ceiling (0–10, including research):
- dependency policy:
- protected paths:

## Environment
- runtime / versions:
- known quirks:

## Lessons
### L-<root-slug> (updated <ISO-date>)
- state: <one-line current truth>
- tried: <refuted approach and reason>
- works: <accepted approach and guard>
- refs: archive/<YYYYMMDD>-<slug>/JOURNAL.md

## Mission log
- <YYYYMMDD>-<slug>: <outcome> (archived)
```

Consolidate rather than append: record refuted cycles, root-cause checkpoints,
reopened defects, and durable successful guards. Update the existing lesson
for the same root cause, rewrite its `state:` line to current truth, and prune
obsolete detail. The journal/archive retain chronology; `PROJECT.md` holds
only what future decisions need.
