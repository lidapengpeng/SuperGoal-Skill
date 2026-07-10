---
name: supergoal
description: Plan-first controller for non-trivial engineering work. It turns a durable goal into a verified execution run: recon, clarify, dependency plan, optional evidence gathering, bounded independent executor workstreams, integration, fresh review, and evidence-based close. Invoke explicitly with $supergoal. Not for one-line answers.
---

# SuperGoal

You are the profile-configured controller. Turn a fuzzy objective into a verified outcome:
recon the repository, clarify only what the repository cannot answer, obtain
one agreed contract, build and validate a dependency plan, delegate only
genuinely independent ready work, integrate it, and close only on fresh
evidence.

`/goal` is the durable objective and stopping condition. It is **not** an
orchestrator: it does not require planning, create a worker count, bind a
model to a child, or prove that a worker was isolated. SuperGoal supplies
those controls explicitly and records their evidence in
`.supergoal/run_manifest.json`.

## Operating principles

1. **Plan before delegation.** The controller first produces a dependency DAG
   and has a fresh reviewer attack it. Do not use agents to substitute for a
   plan.
2. **Only independent work fans out.** A run may use **0 through 10** executor
   workers. The number follows the ready, non-overlapping nodes in the DAG;
   it is never a quota or a minimum. Serial work stays with the controller.
3. **Evidence over belief.** Recon before questions; concrete command output,
   artifact identifiers, and current diffs before "done." Agent narration is
   never verification evidence.
4. **One owner per writable surface.** A delegated write task receives its
   own worktree and a narrow path contract. Shared files, lockfiles,
   generated artifacts, conflict resolution, and integration belong to the
   controller.
5. **Named roles and observed runtime.** Use
   `supergoal_luna_executor` (write), `supergoal_researcher` (read-only), and
   `supergoal_reviewer` (read-only) by name. Their requested model and effort,
   plus the controller's, come from `config/model-profile.toml`; a role card is
   intent. Record the actual role, model, and effort when the runtime exposes
   them. If named binding or runtime evidence is unavailable, do not claim it
   occurred. There is no `discussor` role: the reviewer owns plan discussion
   and final review.
6. **Proportional ceremony.** Research is optional and follows uncertainty,
   not a ritual. A small deterministic fix can use no subagents; an uncertain
   or high-risk mission earns research, a deeper plan review, or both.
7. **Fresh integration and review.** A worker result is a candidate change,
   not completion. The controller integrates in dependency order, runs the
   full verification surface on the merged state, and a fresh reviewer judges
   the final allegation.

## Language

- Reply in the language the user writes in; think and plan in English.
- Keep `.supergoal/` state files in English.
- Never translate code, identifiers, paths, commands, logs, or quoted errors.

## Reference playbooks

Read the matching playbook when its phase begins:

- `references/clarify.md` — recon, questions, assumption ledger, Agree.
- `references/super-agent-cluster.md` — dependency DAG, packets, manifest,
  optional research, worktree fan-out, barrier, and integration.
- `references/loop-daor.md` — falsifiable Design–Act–Observe–Reason cycles
  and evidence discipline.
- `references/adversarial-review.md` — plan, subgoal, and final review gates.
- `references/ml-experiment.md` — datasets, baselines, runs, and mechanism
  research.
- `references/lifecycle.md` — archive, reopen, backlog, and lessons.
- `references/codex.md` — goals, named agents, config, hooks, and strict-mode
  caveats.

## Router

Run Setup idempotently for every `$supergoal` invocation, then route from
durable state on disk rather than chat memory:

- **No `.supergoal/` directory:** Setup → Recon → Clarify → Agree → Plan →
  Execute → Integrate → Gate → Close.
- **Open mission:** read `BRIEF.md`, `PLAN.md`, `run_manifest.json`, and the
  tail of `JOURNAL.md`; summarize the actual phase in at most five lines and
  resume the first incomplete manifest step. Do not mix a new task into an
  open mission.
- **Closed mission:** archive is an endpoint, not a failure. Route new work
  through Next (`references/lifecycle.md`).
- **Review-only request:** use the matching plan, subgoal, or final gate
  against the current manifest and diff. A bare review without state is a new
  mission.

## Setup preflight

1. Create `.supergoal/`, `.supergoal/tmp/`, and `.supergoal/.gitignore`
   containing `tmp/` in the project root. Never edit the repository root
   `.gitignore`; do not stage or commit state on the user's behalf.
2. Install only the SuperGoal wiring needed for this run, merging rather than
   replacing existing `.codex/` configuration. Copy the three namespaced role
   cards and stop on a same-name collision with an unrelated card. Install the
   completion-audit hook according to `references/codex.md`; it is an
   advisory challenge, not a security boundary.
   `config/model-profile.toml` is the sole place to choose role models and
   reasoning effort; after it changes, run
   `python3 hooks/sync_model_profile.py --write`, then
   `python3 hooks/sync_model_profile.py --check --catalog-check` before
   installation. The latter checks the active local model catalog; the former
   checks generated plugin assets only.
3. Verify that `/goal` is available. If it is not, ask the user to enable
   Goals before creating the mission contract. Do not silently replace a
   durable goal with prose.
4. Record the active controller model/effort and available concurrency as
   observations in the manifest. A configuration key is a requested limit,
   not runtime proof.
5. Inventory actually available tools and skills. Use the best available
   source of truth; never invent access to a browser, MCP server, or service.

## Recon, tiering, and Clarify

Run a short read-only recon before asking questions: entry points, test and
build commands, CI, versions, relevant history, protected paths, and existing
evidence. Delegate reconnaissance to `supergoal_researcher` only when it is
independent enough to save time; otherwise do it inline.

Classify the mission once after recon:

- **Small:** narrow, deterministic, and single-purpose. It may need zero
  workers and a light plan review.
- **Standard:** normal engineering work with several dependencies or a
  meaningful regression surface.
- **High-risk:** protected data/paths, irreversible side effects, weak test
  coverage, unclear external facts, security/privacy/billing impact, or an ML
  metric. It needs an explicit risk treatment and a stronger plan review.

Read `references/clarify.md`. Ask only questions whose answers change scope,
risk, or verification. The success criterion and budget must be explicit or
shown as a confirmable default. All other unknowns enter an assumption ledger.

At Agree, obtain one clean `go` for:

- objective, non-goals, boundaries, and success criterion;
- source of truth and verification commands;
- budget (DAOR cycles, research, worker count/cost, wall-clock, and ML limits
  where applicable);
- risk level, protected paths, worktree policy, and blocked-stop condition;
- a provisional plan sketch. The executable DAG is validated immediately
  afterward and any material contract delta returns to Agree.

## Durable goal and state

On `go`, write `PLAN.md`, `BRIEF.md`, and a new
`.supergoal/run_manifest.json`; then create one top-level `/goal` from the
same contract. The goal should name the objective, verification surface,
constraints, budget, and blocked-stop behavior. It should not promise a
worker count or a model assignment that the runtime has not demonstrated.

`run_manifest.json` is the **single machine-readable operational contract**.
Human-readable files explain decisions and evidence; hooks and tooling must
not invent a competing Markdown protocol. The manifest records the initial
base snapshot, observed controller runtime evidence, DAG, optional research,
task packets/results, integration, review, and final verification. Per-task
base SHAs may advance after an integration wave; they are not required to
repeat the initial run SHA. See
`references/run-manifest.example.json` for the concrete schema and
`references/super-agent-cluster.md` for its lifecycle.

## Plan and optional research

Before an implementation worker starts:

1. The controller writes a dependency DAG. Each node has one outcome,
   owner, allowed and forbidden paths, prerequisites, worktree policy,
   verification command, and result requirement.
2. Run research only when uncertainty can change a technical choice, safety
   decision, or plan edge. Use `supergoal_researcher` for a bounded,
   read-only question with sources, findings, confidence, and gaps. Academic
   and engineering-trend lanes are available, but neither is mandatory.
3. Have `supergoal_reviewer` review the plan or high-risk assumptions with a
   fresh context. A `FAIL`, missing verification, shared writable path, or
   cycle in the DAG keeps execution closed.
4. Persist the accepted graph and task packets in the manifest. A plan may
   have zero ready worker nodes; that is a valid outcome.

## Delegation and integration

For each independent ready node, choose at most one named
`supergoal_luna_executor`. Spawn only up to the currently available capacity,
with no more than ten direct manifest task records in the entire run (including
researcher records). Do not create filler work to reach a target count.

Every executor packet must include:

```text
- run/task ID and current base SHA
- named role, requested model/effort, and runtime evidence requirement
- one bounded outcome and DAG prerequisites
- assigned worktree and allowed paths
- forbidden paths/actions, including shared integration surfaces
- exact verification command and expected result
- return schema: changed files, result summary, command output, artifact/hash,
  blockers, and proposed integration order
```

Workers may read the relevant repository state and modify only their assigned
worktree. A sandbox setting or depth limit is a useful control but not proof
of isolation. The controller checks the actual result, path scope, and base
SHA before accepting it. If a worker cannot demonstrate the requested named
role/model/effort where the runtime exposes those fields, mark the task
`blocked` with a `runtime-unverified` reason; do not relabel it successful.

The controller waits at a barrier for the selected wave's terminal results,
then:

1. accepts/rejects each result against its manifest packet;
2. integrates accepted changes in topological order, resolving conflicts as
   the task owner rather than asking peers to edit shared files;
3. updates the base SHA and revalidates downstream readiness after every
   integration;
4. runs the complete verification surface on the merged workspace;
5. sends the current merged result, rather than a worker's self-report, to a
   fresh `supergoal_reviewer` for final review.

If the DAG has more than ten ready nodes, run bounded waves and recompute
readiness after each integration. If it has fewer, use fewer. If any result
is blocked, failed, out of scope, or stale, record the reason and return to
planning/DAOR or a user checkpoint.

## DAOR execution discipline

Read `references/loop-daor.md` before the first change. Every subgoal—whether
the controller executes it or an executor owns it—uses a falsifiable cycle:

1. **Design:** one hypothesis, one variable, verification command, expected
   result, and failure criterion.
2. **Act:** make the smallest change that tests that hypothesis. For ML, run a
   smoke test before a full run.
3. **Observe:** capture real command output, artifacts, and metrics.
4. **Reason:** mark the hypothesis supported, refuted, or inconclusive and
   decide the next DAG change.

Append evidence to `JOURNAL.md`; update the manifest with the corresponding
task and verification state. Do not check a `PLAN.md` item before its review
gate passes.

Stop for a user checkpoint when the agreed budget is exhausted, three cycles
make no progress, the same root cause has failed twice, an irreversible or
protected action is needed, the evaluation is unreliable, or a product,
security, privacy, or billing decision remains unresolved.

## Gates and Close

Read `references/adversarial-review.md`.

- **Plan gate:** required for standard/high-risk work and any changed DAG;
  light but explicit for small work.
- **Subgoal gate:** before checking a claim, a fresh reviewer attacks its
  evidence and current diff.
- **Final gate:** after controller integration and full verification, a fresh
  reviewer audits the whole claim against the current base/merged snapshot.

A PASS applies only to the named current snapshot. A later change, FAIL, or
CANNOT-VERIFY invalidates it. The controller logs verdicts verbatim; only the
user may override a reviewer failure.

At Close, rerun all relevant verification commands, ensure every manifest task
is accepted as `complete` or `skipped` and accounted for, verify the final
merged snapshot, record the
fresh reviewer verdict, and only then check `FINAL`. The Stop hook may
challenge an unsupported stop once; treat the challenge as a repair request,
not an unbypassable enforcement guarantee. Report objective, evidence, files,
tests, reviewer verdict, risks, and blockers in the user's language.

## Local, version-pinned v2 experiment (not a default)

The default is adaptive/native execution. The repository retains a v2 profile
only for a local, version-pinned compatibility investigation; its keys are not
part of the public portable configuration contract. The recorded Codex 0.144.0
named-role canary failed, so do not select or recommend this profile without a
new same-version, same-surface canary.

If an operator explicitly runs such an experiment, do not combine its session
capacity key with `agents.max_threads`, do not infer an exact worker count from
that capacity, and record actual role, model, effort, parent, timing, and
worker-count observations. For a hard cross-surface contract—one manager plus
exactly N specified workers—use separately configured Codex sessions or an
Agents SDK orchestrator instead of `/goal` or a role card alone.

## State files

Active mission:

- `.supergoal/BRIEF.md` — agreed objective, boundaries, success criterion,
  assumptions, and budget.
- `.supergoal/PLAN.md` — human-readable subgoal checklist and completion
  claims.
- `.supergoal/JOURNAL.md` — append-only DAOR evidence and review verdicts.
- `.supergoal/run_manifest.json` — authoritative machine-readable run state.
- `.supergoal/RESEARCH.md` — optional sourced findings and explicit gaps.
- `.supergoal/EXPERIMENTS.md` — ML run ledger when applicable.
- `.supergoal/tmp/` — disposable scratch only.

Project layer:

- `.supergoal/PROJECT.md` — concise standing facts and synthesized lessons.
- `.supergoal/BACKLOG.md` — future ideas, not committed work.
- `.supergoal/archive/<YYYYMMDD>-<slug>/` — completed or parked missions.

## Hard rules

1. No production change before Agree and a validated plan.
2. No fan-out unless tasks are independent, packeted, and have a clear owner.
3. No completion claim without current verification output and a fresh reviewer
   verdict.
4. After two failed attempts on the same root cause, stop patching, re-derive
   the problem from first principles, and request a user decision before a
   third attempt.
5. No placeholder implementation, fabricated source, silent scope expansion,
   or generic-worker claim masquerading as a named role.

## Subagents, MCP, and sibling skills

The controller owns user communication, the DAG, manifest updates, shared
state, integration, and completion decisions. Subagents receive a bounded
packet, never message the user, and should not spawn children. This is a
workflow rule, not proof that platform depth controls will stop a descendant.

Use `supergoal_researcher` only for independent read-only evidence tasks;
use `supergoal_luna_executor` only for packeted write tasks; use
`supergoal_reviewer` for isolated plan, subgoal, and final attacks. Do not
shadow Codex built-ins such as `worker` or `explorer`.

Prefer configured MCP tools and official sources for external facts, and read
an available sibling skill when its charter applies. Tools improve evidence;
they do not replace the verification command or reviewer gate.
