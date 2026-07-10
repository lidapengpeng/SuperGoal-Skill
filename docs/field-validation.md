# Field-validation checklist

Configuration files, role cards, and schema tests prove requested behavior or
structural validity. They do **not** prove that a live Codex session selected a
role, model, effort, sandbox, depth, or concurrency shape. Keep those classes
of evidence separate.

The adaptive SuperGoal contract has no fixed worker minimum. A valid run may
have zero task records; a larger run may have up to ten. The following checks
are the acceptance measurements for the first real missions.

## Evidence labels

- **Documented:** official behavior or schema described in this repository.
- **Configured:** TOML/hook/role configuration parses and is installed.
- **Structurally validated:** local tests accept valid inputs and reject known
  malformed inputs.
- **Observed:** a dated live session/runtime artifact demonstrates behavior.
- **Unproven:** no observation exists; do not upgrade configuration into a
  runtime claim.

## Required measurements

| # | Measurement | Passing evidence | What it decides |
| --- | --- | --- | --- |
| FV1 | Manifest plan phase accepts zero tasks. | A valid plan manifest with `tasks: []` and a PASS plan review. | Small/serial work is not forced to fan out. |
| FV2 | Task count and status closure. | Validator accepts 0–10 records and rejects more, duplicate IDs, or a complete run with a task other than `complete`/`skipped`. | Capacity is a ceiling and completion state is honest. |
| FV3 | DAG integrity. | Validator rejects missing dependencies and cycles; a real run records prerequisite closure before a node starts. | Ready-node scheduling is based on dependencies, not narration. |
| FV4 | Write isolation contract. | Validator rejects owned/forbidden overlap and any writer path/worktree collision; a real run preserves assigned worktree evidence. | Parallel writes have an auditable boundary. |
| FV5 | Per-task base snapshot. | Validator rejects an empty or implausible task `base_sha`; integration records a new merged base before downstream scheduling. | Results are not merged against an unknown or stale base. |
| FV6 | Complete task evidence. | Validator rejects a complete task without result, evidence, or `output_sha256`; a real task includes raw verify output. | Worker prose cannot substitute for evidence. |
| FV7 | Executor named-binding canary. | `manifest_audit.py --binding-canary` validates an observation with matching executor role, requested model/effort from `[executor]`, and evidence. | A particular runtime/surface can support that configured named-executor claim. |
| FV8 | Controller/reviewer runtime. | A dated runtime observation shows the configured controller and fresh reviewer model/effort where those fields are exposed. | Documentation distinguishes requested from observed runtime. |
| FV9 | Optional research routing. | One `not_needed` run and one bounded researcher run show research only when uncertainty changes a plan decision. | Research is evidence-driven rather than mandatory ceremony. |
| FV10 | Barrier and central integration. | A multi-node run records terminal results, controller acceptance/rejection, topological integration, and full merged verification. | Workers do not self-integrate or self-complete. |
| FV11 | Fresh final review. | Final reviewer evidence is tied to the current merged snapshot and a later change stales it. | An older PASS cannot close changed work. |
| FV12 | Stop-hook behavior. | A deliberately incomplete manifest triggers one audit challenge; the next stop behavior is recorded honestly. | The hook is an advisory completion audit, not an unbypassable control. |
| FV13 | Strict v2 adapter. | A version-pinned canary records named-child role/model/effort, capacity, parent/topology observations, and `fork_turns="none"`. | Whether that exact build may use the opt-in adapter. |

## Runnable checks

Run these against the installed copy, not only this source checkout.

### Manifest contract

1. Validate the shipped
   [`run-manifest.example.json`](../references/run-manifest.example.json).
   From this source checkout, use `python hooks/manifest_audit.py --manifest
   references/run-manifest.example.json`; an installed mission instead passes
   its `.supergoal/run_manifest.json` path to the copied audit.
2. Create negative fixtures for: missing controller evidence, missing plan
   review, more than ten tasks, duplicate IDs, cycle, missing dependency,
   empty/implausible task base SHA,
   owned/forbidden overlap, writer path/worktree collision, completed task
   missing result/evidence/output hash/runtime object, incomplete integration,
   missing final reviewer, and missing final verification.
3. Confirm no check reads private SQLite tables, rollout transcript formats, or
   a duplicated Markdown packet schema.

### Executor binding canary

1. Start a small mission with one genuinely independent executor task.
2. Spawn `supergoal_luna_executor` with `fork_turns="none"` when the runtime
   supports named-role metadata.
3. Save an explicit observation JSON with task ID, `agent_role`,
   `requested_model`, `requested_reasoning_effort`, observed `model`,
   observed `reasoning_effort`, and evidence.
4. Run `manifest_audit.py --binding-canary <observation.json>`.
5. Copy the observed runtime object into the completed task manifest record.

Pass only if the observed values match the requested executor profile values.
A role card, model catalog, UI label, or worker self-report cannot fill
missing runtime evidence. Failure or absence means a `blocked` task with a
`runtime-unverified` reason—not a fallback claim that a generic child used
the configured executor runtime.

### Optional research routes

Exercise both paths in real work:

- **Not needed:** recon resolves the decision; manifest `research.status` is
  `not_needed` with a concise reason.
- **Needed:** a bounded `supergoal_researcher` task returns sources,
  confidence, conflicts, and gaps; the plan review cites which DAG decision
  changed because of it.

For academic research, record publication/track/version rather than inferred
venue prestige. For engineering trends, record primary artifacts separately
from community signals. A source count by itself is never a passing result.

### Multi-task integration

1. Create two truly independent write nodes with disjoint paths and worktrees.
2. Verify both packets carry the current snapshot SHA for their wave, distinct
   owned paths, forbidden shared surfaces, and deterministic commands. A later
   wave may legitimately use a newer task SHA than the run's initial SHA.
3. Wait for terminal results, reject any stale/out-of-scope return, and
   integrate accepted work in declared topological order.
4. Record the merged verification output, then run a fresh final review.
5. Change a relevant file after review and verify the final PASS becomes stale
   until a new verification/review run occurs.

Do not use this test to infer a fixed concurrency level; it validates the
workflow regardless of whether the platform schedules tasks serially or in
parallel.

### Strict v2 profile

Use this only if strict mode is intentionally selected:

1. Pin the Codex version and enable v2 only after confirming this local,
   undocumented compatibility surface applies to that build.
2. Use the v2 session cap alone—never combine it with `agents.max_threads`—and
   do not infer an exact worker count from it.
3. Set child spawns to `fork_turns="none"` only where that build exposes it.
4. Expose spawn metadata where supported, run the binding/topology canary, and
   retain the output with the mission evidence.

A passing result is specific to that version and surface. It does not prove an
exact worker count under Sol/Ultra or a strict no-descendant guarantee. Use
separate configured sessions or an Agents SDK orchestrator when that guarantee
is required.

## Outcome log

Add dated entries below as real missions run. Preserve failures and supersede
them rather than rewriting history. Each entry should label the evidence class
above, link or name the retained artifact, and state the operational decision.

### 2026-07-09 — FV7 project-local named Luna binding canary

- evidence class: observed failure
- environment: `codex-cli 0.144.0`; temporary Git repository with
  `.codex/agents/supergoal_luna_executor.toml`; v2 enabled, capacity `2`,
  `hide_spawn_agent_metadata = false`, and `fork_turns="none"`
- artifact: [failed binding-canary observation](canary-20260709-luna-binding.md)
- result: UNPROVEN — no child was created, no generic fallback was allowed,
  and role/model/effort are therefore unverified
- decision: this tested CLI surface must not claim native named-Luna binding.
  Use an explicitly configured Luna session or an Agents SDK orchestrator until
  an upgraded, same-surface canary passes.

```markdown
### <YYYY-MM-DD> — FV7 Luna binding canary

- evidence class: observed
- environment: <Codex version / surface>
- artifact: <observation JSON path or digest>
- result: PASS|FAIL|UNPROVEN
- decision: <what this permits or prohibits>
```
