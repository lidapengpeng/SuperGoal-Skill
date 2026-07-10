# SuperGoal adaptive pipeline redesign

Date: 2026-07-09

## Decision

SuperGoal now treats `/goal` as a durable objective and completion condition,
not as a workflow engine. The default profile architecture is:

```text
Sol/ultra controller
  -> recon + Agree
  -> dependency DAG + fresh plan review
  -> optional Luna/xhigh research where uncertainty changes the plan
  -> 0..10 independent Luna/xhigh task records
  -> controller-owned integration + full merged verification
  -> fresh Sol/max review + completion audit
```

This follows the documented separation of durable goals, custom agents, and
subagent configuration: a goal stores an objective; named cards request a
runtime; capacity configuration limits admission; none of those independently
enforce planning, a fan-out count, or cross-surface role binding. See the
official [Goals](https://developers.openai.com/codex/use-cases/follow-goals/),
[Subagents](https://developers.openai.com/codex/multi-agent/), and
[Models](https://developers.openai.com/codex/models/) documentation.

## What changed

| Previous failure mode | New rule |
| --- | --- |
| Every mission paid for a forced research/fan-out wave. | The controller uses 0–10 task records only when the DAG contains genuinely independent work; research is optional. |
| Generic-child behavior was described as named role binding. | Three namespaced cards are invoked by name; a completed executor task needs observed `runtime` evidence, otherwise the binding is unproven. |
| Markdown, hook parsing, and private runtime data competed as state. | `run_manifest.json` is the single machine-readable operational contract; human documents remain evidence and explanation. |
| Multiple writers could collide in one workspace. | Each independent writer has a unique worktree, base SHA, owned paths, forbidden paths, verification command, and result contract; the controller integrates. |
| A thread/depth configuration was presented as a strict hierarchy guarantee. | It is documented as capacity/defence in depth only; topology claims need a runtime canary. |
| Completion leaned on worker claims or old reviews. | Full merged verification and a fresh profile-configured reviewer are required on the current snapshot. |

## Role contract

- **Controller:** `[controller]` profile (default: `gpt-5.6-sol` / `ultra`);
  owns plan, manifest, integration, user communication, and evidence synthesis.
- **`supergoal_luna_executor`:** `[executor]` profile (default:
  `gpt-5.6-luna` / `xhigh`); performs one independent write task in a supplied
  worktree.
- **`supergoal_researcher`:** `[researcher]` profile (default:
  `gpt-5.6-luna` / `xhigh`); performs one optional read-only evidence task.
- **`supergoal_reviewer`:** `[reviewer]` profile (default: `gpt-5.6-sol` /
  `max`); independently attacks plan and integrated completion claims.

The executor/researcher/reviewer cards are deliberately namespaced so they do
not alter Codex built-in roles. A card is a request, not evidence of observed
runtime. The task `runtime` object captures the latter for completed executor
tasks.

## Manifest contract

The validator consumes version-1 `.supergoal/run_manifest.json` rather than
parsing a separate Markdown protocol or private Codex state. It records:

- run identity, initial base SHA, lifecycle phase, and requested/observed
  controller runtime evidence;
- plan review and optional research decision/evidence;
- up to ten direct task records, each with parent, role/runtime request,
  base SHA, dependencies, write/path/worktree boundary, verification, status,
  result/evidence/hash, and observed runtime for completed executor work;
- controller integration evidence, fresh final review, and full final
  verification.

The concrete conforming shape is in
[`references/run-manifest.example.json`](../references/run-manifest.example.json).
The validator rejects cycle/dependency errors, missing/malformed task base
identity, path overlap, writer collisions, incomplete result proof,
and a complete phase lacking integration/final review/final verification. The
controller—not the portable validator—rejects a stale result during
integration.

## Strict mode remains optional

The default config uses the public `[agents]` capacity setting for up to ten
spawned child threads. The local version-pinned v2 adapter is separate and
undocumented as a portable surface: use it only after a same-surface canary,
do not infer an exact worker count from its session cap, and do not combine
`agents.max_threads` with the v2 cap.

Even then, Sol/Ultra may delegate proactively, and a depth limit is not a
hard no-descendant guarantee. For a strict manager-plus-N contract, use
separate configured Codex sessions or an Agents SDK orchestrator rather than
relying on `/goal` or a role card.

## Acceptance checks

1. Config/cards parse and install under the three exact names.
2. The manifest example passes validation; negative fixtures cover missing
   evidence, invalid DAGs, stale paths/worktrees, and incomplete completion.
3. A zero-task plan validates, proving the system does not require fan-out.
4. A two-task integration demonstration proves worktree/path boundaries,
   controller integration, full merged verification, and fresh review.
5. A one-worker binding canary records actual role/model/effort against the
   requested executor profile before any strong runtime claim is made.
6. Strict v2 claims stay version- and canary-scoped; absent evidence is
   reported as unproven.

See [`field-validation.md`](field-validation.md) for the live measurement
protocol and evidence labels.
