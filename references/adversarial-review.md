# Adversarial review protocol (Gates)

Maker and checker must use different contexts. The controller may assemble
evidence, but it may not turn its own conclusion into a completion verdict.
Use the named, read-only `supergoal_reviewer` with the `[reviewer]` profile
(shipped default: Sol/max) for plan and final review. A card requests that
runtime; record actual runtime evidence when it is available rather than
assuming it.

## Gates

1. **Plan gate:** after the controller builds the dependency DAG and before
   any write worker starts. Required for standard/high-risk missions; small
   missions receive a compact review, not an unlogged skip. The reviewer
   attacks scope, verification, dependencies, worktree/path ownership,
   research gaps, and whether every proposed worker node is genuinely
   independent.
2. **Subgoal gate:** before checking a `PLAN.md` item. The reviewer attacks
   the claim, its current snapshot, verify output, and any worker result.
3. **Final gate:** after controller integration and complete verification.
   A fresh reviewer audits the current merged diff and all claimed outcomes.

The plan review is stored at `plan.review` in `run_manifest.json`; the final
review is stored at top-level `review`. Both use:

```json
{
  "role": "supergoal_reviewer",
  "verdict": "PASS",
  "evidence": ["...current evidence..."]
}
```

`PASS` in the example is not a default: the validator only accepts it once an
actual fresh reviewer has returned that verdict. `FAIL` and `CANNOT-VERIFY`
remain valid review outcomes in the journal but cannot advance the plan or
complete a run.

## Reviewer packet

Explicitly invoke `supergoal_reviewer` by name. Give it the allegation to
attack, not a conclusion to endorse:

- current run ID, base SHA, and integrated snapshot identity;
- relevant `BRIEF.md`, `PLAN.md`, manifest node(s), and journal evidence;
- the raw verification commands and outputs;
- task ownership, worktree, allowed/forbidden paths, and dependency edges;
- the actual current diff. Do not curate the diff or omit files on the
  controller's behalf;
- for final review, the full merged verification surface and any unresolved
  risks or blocked tasks.

Do not give the reviewer the controller's preferred answer. A reviewer who
only confirms a supplied interpretation cannot catch an omitted file,
over-broad change, stale baseline, or hidden dependency.

## Plan-review checklist

The reviewer must be able to answer:

- Does the DAG pursue the agreed objective rather than a plausible substitute?
- Is each success condition observable, current, and difficult to game?
- Are prerequisites complete and is the graph acyclic?
- Is research actually needed for an unresolved decision, and are its gaps
  explicit rather than silently assumed away?
- Does each writable task have a unique worktree and non-overlapping owned
  paths unless it depends on the earlier owner?
- Are shared files and integration reserved for the controller?
- Is the number of worker nodes justified by independent ready work, with zero
  workers accepted when delegation adds no value?
- Are destructive, security, privacy, billing, and ML risks treated before
  execution?

A missing verification command, cycle, path collision, unresolved high-risk
assumption, or unsupported role/runtime claim is a blocking finding.

## Subgoal and final checklist

For every completion allegation, attack:

- correctness, regressions, security/privacy impact, error handling, and
  generated/lockfile drift;
- whether the diff is within the task's allowed paths and the controller
  integrated it in the expected order;
- test honesty: the command, output, artifacts, environment, and snapshot;
- whether an ML result has a comparable baseline, controlled ablation, and a
  real metric rather than cherry-picked narration;
- leanness: dead code, duplicated abstractions, placeholder paths, broad
  refactors, and unexplained dependencies;
- whether all terminal manifest tasks, integration evidence, and final
  verification describe the same merged state.

## Verdict protocol

Return exactly one of:

- **PASS:** no blocking counterexample found; list non-blocking notes
  separately.
- **FAIL:** name a concrete counterexample, minimal reproduction/reasoning,
  and what must change.
- **CANNOT-VERIFY:** name the exact missing command, artifact, runtime fact,
  or access needed to decide.

Every verdict is authoritative only for its named snapshot. A later workspace
change, `FAIL`, or `CANNOT-VERIFY` stales an older `PASS`. The controller logs
the verdict verbatim in `JOURNAL.md`, attaches evidence to the relevant
manifest object, and may request another review; it may not soften or
reinterpret a failure. Only the user can explicitly override a reviewer
failure.

## Handling findings

- **Plan FAIL:** repair the DAG, research gap, ownership boundary, or contract
  and rerun the plan gate. A material objective/budget/blast-radius change
  returns to Agree.
- **Subgoal FAIL:** reopen the node with the counterexample as input. After
  two failures on the same root cause, re-derive from first principles and
  request a user decision before a third attempt.
- **CANNOT-VERIFY:** add the missing evidence as a bounded node or research
  task; do not relabel absence as PASS.
- **Reviewer unavailable:** do not check claims or complete the run. Report
  Setup/runtime failure at the current checkpoint.

The Stop hook can flag an inconsistent final state, but it does not replace a
fresh reviewer and cannot prove scientific or product correctness.
