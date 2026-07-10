# DAOR loop discipline (Execution)

One cycle is one controlled experiment. Do not “change something and see.”
The agreed contract supplies the global stop condition; the dependency DAG and
DAOR supply the local discipline.

## Observe-0

Before the first change to a verification surface:

- run the agreed evaluation on the untouched or current integrated state;
- record baseline metric, exit code, command, timestamp, and relevant
  environment (commit, seed policy, dataset version, hardware);
- for greenfield work, record the failing or absent result as the baseline.

Without a baseline, improvement is unfalsifiable. If a later integration
changes that surface, rerun it; old evidence does not transfer automatically
to a new merged SHA.

## The four phases

The controller's dependency plan is not the per-cycle Design step. The DAG
chooses a ready node and its ownership boundary; each DAOR cycle tests one
falsifiable hypothesis inside that node.

### 1. Design

- Check relevant `.supergoal/PROJECT.md` lessons before repeating a known
  failed approach.
- State one hypothesis: “the bottleneck is X; changing Y should move metric Z
  by roughly dZ.”
- Change one variable. If a composite change is necessary, name it and plan a
  follow-up ablation or guard.
- Write the verify command, expected result, and failure criterion before
  acting. If no possible observation can refute it, redesign the experiment.
- If a named executor will act, put the hypothesis and these conditions in its
  manifest packet. It receives a base SHA, worktree, owned and forbidden
  paths; it does not invent scope.

### 2. Act

- Make the smallest defensible change that tests the hypothesis. No drive-by
  refactor, new dependency, or shared-file edit outside the accepted plan.
- For delegated writes, work only in the assigned worktree. Return the actual
  changed paths and command output; the controller decides whether to
  integrate.
- For ML, smoke-test on a small budget before a full run. Record checkpoints
  and resume commands.

### 3. Observe

- Record actual outputs only: test results, logs, metric files, artifacts,
  profiler output, and current diff identities.
- Quote raw numbers and relevant log lines. “The worker said it passed” is not
  evidence.
- For a completed delegated task, store a non-empty result, evidence, and
  `output_sha256` in the manifest. Record the observed `runtime` object when
  named role/model/effort evidence is available; requested card fields are not
  a substitute.
- Kill clearly diverged long runs early and record the kill as an observation.

### 4. Reason

- Compare expected and observed result: supported, refuted, or inconclusive.
- Name the root cause and choose the next action: accept, replan, investigate,
  integrate, retry, or request a user checkpoint.
- A refuted expectation or gamed check becomes a permanent guard in the
  verification plan. Update the relevant `L-` lesson in `PROJECT.md` rather
  than rediscovering it later.

## JOURNAL.md entry format

Keep the journal append-only and human-readable. `run_manifest.json` is the
machine-readable execution contract; do not maintain a second parser-specific
protocol in Markdown.

```markdown
## C<n> <ISO-datetime> <task-id> ATTEMPT <a>
- snapshot: <base SHA and current merged SHA>
- design: <hypothesis; one variable; verify command; expected result>
- act: <controller action or executor worktree/result>
- observe: <quoted output, artifact identity, output SHA when applicable>
- reason: <supported|refuted|inconclusive; root cause; next step>
- manifest: <run ID / task ID / current status>
- reviewer: <role/run ID and PASS|FAIL|CANNOT-VERIFY when a gate ran>
```

Plan and final gates are also journaled, but their authoritative structured
state lives in `plan.review`, top-level `review`, and `final_verification` in
the manifest:

```markdown
## PLAN GATE <ISO-datetime>
- snapshot: <base SHA>
- reviewer: supergoal_reviewer
- verdict: PASS|FAIL|CANNOT-VERIFY
- evidence: <one or more concrete findings>

## FINAL GATE <ISO-datetime>
- snapshot: <current integrated SHA>
- full-verification: <command set, timestamp, exit codes, artifact identities>
- reviewer: supergoal_reviewer
- verdict: PASS|FAIL|CANNOT-VERIFY
```

Any later relevant change stales a prior PASS. Do not select a convenient
historical review after integration changed the snapshot.

## DAG and integration boundaries

- A task becomes ready only when every `depends_on` task has a terminal,
  accepted result and its base SHA remains valid.
- Independent writable tasks receive unique worktrees and non-overlapping
  `owned_paths`; a task may not list a path in both `owned_paths` and
  `forbidden_paths`.
- The controller owns rebasing, merging, shared files, conflict resolution,
  lockfiles, generated artifacts, and full-suite verification.
- After each integration, record the new base SHA and recompute readiness.
  Downstream work based on an old SHA is stale until rebased or replanned.

## Stop controls

1. **Iteration cap:** the agreed DAOR budget (default 10 cycles unless the
   contract says otherwise).
2. **No-progress:** three consecutive cycles without meaningful test/metric
   improvement, or two failures on the same root cause.
3. **Resource ceiling:** approved wall-clock, research, maximum direct task-record count,
   and ML GPU/full-run limits.

Also pause immediately for protected paths, destructive or irreversible
actions, unreliable evaluations, or unresolved product/security/privacy/
billing decisions. A blocked task is a truthful terminal state, not a reason
to fabricate a replacement result.

## Evidence ladder

1. Repository source, tests, fixtures, CI, logs, and artifacts.
2. Official docs, specifications, API references, and release notes.
3. Upstream issues, PRs, changelogs, and papers.
4. Reputable community discussion, corroborated before it drives a decision.
5. Model memory, never sufficient for version-sensitive facts.

Use optional research when an unresolved fact at these levels changes a plan
edge. Record source, confidence, and gaps in the manifest/research note; do
not create arbitrary shards or source quotas.

## Context hygiene

The controller keeps decision context and delegates only bounded independent
work. Pass subagents paths, task IDs, and small relevant excerpts—not full
transcripts. After a reset, re-read `BRIEF.md`, `PLAN.md`, the manifest, and
the journal tail before resuming. Disk state is the handoff, not chat memory.
