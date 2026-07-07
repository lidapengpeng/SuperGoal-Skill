# Project lifecycle (Next phase)

The mission layer answers "how do I finish this hard task safely?". The project
layer answers "what happens when it is finished and the project continues?".
Two layers, kept apart on purpose:

- **Mission layer** - bounded and machine-checked: one active `BRIEF.md`,
  `PLAN.md`, `JOURNAL.md`, one `/goal`, one final gate. The Stop hook enforces
  it.
- **Project layer** - long-lived and human-judged: a backlog of ideas, a
  memory file of standing facts, and an archive of finished missions. The Stop
  hook ignores it.

```text
BACKLOG idea
  -> compact intake (Clarify)
  -> contract (Agree)
  -> DAOR cycles (Loop)
  -> adversarial final gate (Gate)
  -> archive (Next)
  -> BACKLOG / next mission
```

## When Next runs

Only from the router's closed-mission branch: `PLAN.md` has a checked `FINAL`
backed by a `## FINAL GATE` section logging `review: PASS`, and the user
brings new work. A closed mission is never auto-resumed; it is an archive
point.

## Classifying the new work

Every incoming idea has exactly one home. Decide before touching anything:

1. **New mission** - the idea has a new outcome, a new success criterion, or a
   new budget. This is the default when in doubt.
2. **Reopen** - the idea is a defect, missing evidence, or a regression against
   the *previous mission's stated success criterion*. It re-litigates work
   already claimed done.
3. **Backlog** - the idea is real but not ready to execute now. It has no
   committed outcome or budget yet.

Park is a separate transition, not a classification: it applies when the
*current* mission is still open but must yield to urgent new work.

## New mission

1. Archive the completed root files (see layout below) - including the cluster
   files (`DRAFT_BRIEF.md`, `RESEARCH.md`, `DESIGN.md`, `DEBATE.md`) when the
   finished mission was standard/high-risk. Delete
   `.supergoal/tmp/.write-audit-baseline` as part of archiving: a baseline taken
   before the move would mass-false-block the next mission's first
   write-capable agent.
2. Create fresh root files: `BRIEF.md`, `PLAN.md`, `JOURNAL.md`, and
   `EXPERIMENTS.md` only if the new mission has runs. Cluster files are
   created lazily by the design waves if the new mission is standard/high-risk;
   do not pre-create them.
3. Prefer a fresh Codex thread - one thread holds one goal (see `codex.md`),
   which keeps the verification surface clean and avoids context
   contamination. `/goal clear` in the same thread is the fallback when a new
   thread is inconvenient.
4. Run a compact Clarify pass pre-filled from `PROJECT.md`. Only the two
   mandatory pins are asked outright - the success criterion and the
   iteration budget (`clarify.md`). Every other dimension (boundaries,
   dependency policy, eval source of truth, default budgets) is stated as an
   assumption-ledger inference drawn from `PROJECT.md` for the user to
   confirm or correct at Agree. A new mission should cost far fewer questions
   than the first one.

## Reopen

1. Append a `## REOPEN <ISO-date>` entry to `JOURNAL.md` naming the defect and
   the success criterion it violates.
2. Add a new unchecked `SG` before `FINAL` in `PLAN.md`.
3. **Uncheck `FINAL`.** A reopened mission must earn a fresh, dated
   `## FINAL GATE`. The Stop hook also enforces this mechanically: a
   `## REOPEN` entry dated after the newest `## FINAL GATE` blocks the
   session while FINAL is checked, so the lazy path (leave FINAL checked,
   let the stale gate cover the defect) no longer exists.
4. Cluster missions only: append a dated `## REOPEN DESIGN NOTE` to
   `DESIGN.md` stating whether the defect invalidates the accepted design. If
   it does, run one debate round (all four reviewers) on the amended design
   before the fix cycle; if not, record the reason and proceed. The existing
   `## FINAL DESIGN INSPECTION` marker keeps the Stop hook's design check
   satisfied; the note keeps the record honest.
5. Run DAOR on the new subgoal, then the final gate again.

## Backlog

Record the idea in `.supergoal/BACKLOG.md` and touch nothing else - no `PLAN.md`
edit, no checkbox. `PLAN.md` is committed executable work that the Stop hook
enforces via `- [ ]`; the backlog is deliberately invisible to the hook so
casual ideas never block a session end. Promote exactly one backlog item into a
mission when you decide to execute it.

Backlog entry template (note: no checkbox):

```markdown
## Idea <ISO-date> - <short title>

- status: candidate
- source: <where it came from, e.g. user idea after <slug> final report>
- possible outcome:
- possible verification:
- risks:
- promote-when: <the condition that turns this into a mission>
```

## Park (incomplete mission, superseded)

This procedure covers missions past Agree (PLAN.md and JOURNAL.md exist). A
mission parked before Agree follows the pre-Agree park rule in
`references/super-agent-cluster.md` instead - the wave artifacts archive with
a note in DRAFT_BRIEF.md.

When urgent work arrives before the current mission closes:

1. Mark every remaining unchecked subgoal `- [!] parked: superseded by <slug>`
   so the Stop hook stops counting it as open work (the hook ignores `- [!]`).
2. Archive the root files to `.supergoal/archive/<YYYYMMDD>-<slug>-PARKED/`.
3. Log a `## PARK <ISO-date>` entry in `JOURNAL.md` before it is archived:
   what was done, what remains, and the resume command.
4. Run intake for the new mission.

Resuming a parked mission restores its root files from the archive back to
`.supergoal/`, reverts the `- [!] parked` markers to `- [ ]`, and continues the
DAOR loop.

## Archive layout

One active mission per set of root files. Finished and parked missions move
into per-mission archive folders:

```text
.supergoal/
  BACKLOG.md
  PROJECT.md
  BRIEF.md          # active mission only
  PLAN.md           # active mission only; the Stop hook reads this
  JOURNAL.md        # active mission only
  EXPERIMENTS.md    # active mission only, if the mission has runs
  DRAFT_BRIEF.md    # active cluster mission only, until promoted at Agree
  RESEARCH.md       # active cluster mission only; register + claims
  DESIGN.md         # active cluster mission only; Stop hook reads its inspection
  DEBATE.md         # active cluster mission only
  tmp/
  archive/
    20260705-initial-docs/
      BRIEF.md
      PLAN.md
      JOURNAL.md
      FINAL-REPORT.md
    20260707-recipe-system-PARKED/
      BRIEF.md
      PLAN.md
      JOURNAL.md
```

Folder names are `<YYYYMMDD>-<slug>` (append `-PARKED` for parked missions). No
mission-ID counter: dates plus slugs are enough to keep folders ordered and
unique, and there is nothing to increment or collide.

## Why archiving is required, not optional

The Stop hook validates a checked `SG<n>` against *any* `JOURNAL.md` section
whose header names it and whose body logs `review: PASS` (`has_pass` in
`hooks/stop_audit.py`). If two missions shared one `JOURNAL.md`, mission 2's
checked `SG1` would be spuriously satisfied by mission 1's `## C3 ... SG1`
PASS entry, and the checkbox-as-claim guarantee would break silently. Archiving each finished mission into its own
folder keeps one mission per journal, which is what makes the hook sound over a
long-lived project.

## PROJECT.md

Thin, durable memory read at every new mission's intake and checked at each
cycle's Design step (`loop-daor.md`). Facts only, not a narrative. Rules: add
an entry only after observed friction (a repeated error, a surprising quirk,
a hard-won fact) - never restate what the repo already documents; keep the
whole file under ~150 lines; prune stale or repo-answerable lines at every
intake. Empirically, a bloated or redundant context file hurts agents more
than no file at all.

```markdown
# PROJECT

## Standing defaults
- eval command:
- default iteration budget:
- dependency policy:
- protected paths:

## Environment
- runtime / versions:
- known quirks: <e.g. eval is flaky unless SEED=0>

## Lessons
- <one line per hard-won fact with no failure history>

### L-<root-slug> (updated <ISO-date>)
- state: <one-line synthesis of the current truth>
- tried: <approach> (C<n>, refuted - <reason>); <approach> (C<n>, refuted - <reason>)
- works: <approach> (C<n>; guard: <the verify command that now catches it>)
- refs: archive/<YYYYMMDD>-<slug>/JOURNAL.md

## Mission log
- <YYYYMMDD>-<slug>: <one-line outcome> (archived)
```

### Lessons consolidation (the memory layer)

`JOURNAL.md` and the archive are the raw chronological record; the `L-`
entries are the synthesized top layer - the only part loaded into context.
One entry per root cause, clustered around the problem, never a diary. The
main thread owns this file; subagents never write it.

Write triggers - consolidate, never bare-append:

- A cycle's Reason verdict is `refuted`: the failed approach joins its
  root's `tried:` line (create the `L-` entry if the root is new).
- Hard rule 4 fires: the checkpoint's diagnosis IS the entry - write it when
  the checkpoint is raised, not later.
- Reopen: update the entry whose `state:` line let the defect through.
- Close: sweep the mission's journal for any of the above that slipped past,
  then fill in `works:` for what finally held.

Consolidation rules:

- Same root slug -> update the existing entry; a second entry for the same
  root is a defect.
- `state:` is rewritten in place, one line, newest truth first. Keep the
  supersession only when the *why* still informs decisions ("used to
  patch X per-caller; the shared guard in Y is the fix") - the timeline
  itself lives in `tried:` and `refs:`, never in the state line.
- Prune at every intake: collapse an old resolved entry to its `state:`
  line alone; delete it once the repo or a permanent guard answers it. The
  `refs:` line keeps the full detail reachable in the archive.
