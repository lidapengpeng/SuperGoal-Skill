# SuperGoal execution cluster

This is the runtime playbook for the adaptive SuperGoal pipeline. The
profile-configured controller plans and integrates. The shipped profile uses
Sol for controller/reviewer and Luna for executor/researcher, but those model
and effort requests come from `config/model-profile.toml`. It delegates only
independent work that has a clear owner, and it may create **zero through ten**
bounded direct task records in a run, including optional research and executor
work. Worker count follows the dependency DAG; it is never a quality signal,
quota, or minimum.

`/goal` stores the mission objective. `run_manifest.json` stores the actual
execution contract and evidence. Neither a goal sentence nor a TOML role card
by itself proves planning, named binding, model selection, sandboxing, depth,
or concurrency.

## Roles

| Responsibility | Named role / requested runtime | Authority |
| --- | --- | --- |
| Controller | `[controller]` profile (default: Sol / ultra) | Owns intake, DAG, manifest, packets, integration, user communication, and completion decision flow. |
| Write execution | `supergoal_luna_executor` / `[executor]` (default: Luna / xhigh) | One independent, packeted write task in one worktree. Returns a result; never self-integrates or self-certifies completion. |
| Evidence gathering | `supergoal_researcher` / `[researcher]` (default: Luna / xhigh) | One bounded read-only question. Returns sources, findings, confidence, and gaps. It is optional. |
| Independent attack | `supergoal_reviewer` / `[reviewer]` (default: Sol / max) | Plan, subgoal, and final review from a fresh read-only context. Its verdict gates claims. |

The role card asks for a runtime; the manifest records the requested fields.
A completed named executor task additionally needs an observed `runtime` object.
If the runtime cannot demonstrate the requested binding, record the task as
unverified or blocked rather than claiming a role/model guarantee.

## Mission route

```text
Setup -> Recon -> Clarify -> Agree -> one /goal
                                      |
                                      v
                            controller creates plan DAG
                                      |
                 optional research only for material uncertainty
                                      |
                                      v
                            fresh plan review / DAG validation
                                      |
              0..10 independent ready executor task records and packets
                                      |
                                      v
                   bounded worker wave(s) + terminal-result barrier
                                      |
                                      v
              controller validates, integrates in dependency order,
                     and runs full merged verification
                                      |
                                      v
                  fresh final reviewer -> Close / replan / checkpoint
```

There is no mandatory research phase and no mandatory fan-out. A deterministic
small fix can have an empty `tasks` array. A high-risk task can require
research and several planning/review iterations before any write task is
ready.

## Controller planning and DAG validation

After Agree, the controller creates a plan-phase manifest and writes a DAG
whose nodes are small enough to own, verify, and integrate. A node must state:

- one outcome and its `id`;
- prerequisites (`depends_on`) and the expected base SHA;
- whether it writes; if it does, its worktree, `owned_paths`, and
  `forbidden_paths`;
- an exact verification command or evidence condition;
- expected result and return evidence;
- requested named role/model/effort.

The controller rejects its own plan before review if it contains a dependency
cycle, an unspecified verification surface, or a write task without a unique
owner. Then `supergoal_reviewer` attacks the plan. A plan does not enter
execution until `plan.review` is PASS and the manifest has a valid DAG.

Research is a plan input, not a required ceremonial phase. Ask one or more
bounded research questions only when a fact could change a design choice,
risk treatment, or DAG edge. Use `supergoal_researcher` for read-only work;
record source URLs/identities, findings, confidence, conflicts, and explicit
gaps in its task evidence or the optional `research` object. Academic and
engineering-trend research are available lanes:

- **Academic:** methods, algorithms, benchmarks, novelty, reproduction, and
  publication/venue metadata. Record venue/track/version rather than
  inferring quality from reputation.
- **Engineering trends:** current releases, bugs, migration experience, and
  community reports. Treat community discussion as a signal until supported
  by a primary artifact.

Use neither lane when repository evidence already resolves the decision. Do
not invent source quotas, fixed shards, or research tasks merely to fill a
worker capacity.

## The single manifest contract

`.supergoal/run_manifest.json` is the only machine-readable execution state.
`BRIEF.md`, `PLAN.md`, `JOURNAL.md`, and optional `RESEARCH.md` remain the
human-readable explanation and evidence trail. Do not make hooks parse a
second Markdown envelope, private SQLite database, rollout transcript, or
agent prose in order to reconstruct a run.

The concrete valid sample is
[`run-manifest.example.json`](run-manifest.example.json). Its version-1 shape
is:

| Field | Meaning |
| --- | --- |
| `version`, `run_id`, `base_sha`, `phase` | Schema version `1`, stable run identity, plan base snapshot, and `plan`, `execution`, or `complete` lifecycle phase. |
| `controller` | Requested controller `model` and `reasoning_effort` from `[controller]` (shipped default: `gpt-5.6-sol` / `ultra`), plus nonempty observed runtime `evidence`. |
| `plan.review` | `supergoal_reviewer` verdict and evidence for the executable DAG. |
| `research` (optional) | `not_needed`, `pending`, or `complete`, plus concise evidence for the research decision when complete. |
| `tasks` | Zero through ten direct task records. Each record has `id`, `parent: "controller"`, role/runtime request, `base_sha`, dependencies, write intent, owned/forbidden paths, worktree, verification, status, result/evidence, and (when complete) output/runtime proof. |
| `integration` | `pending` or `complete`, plus evidence that the controller integrated the accepted work. |
| `review` | Fresh final `supergoal_reviewer` verdict and evidence for the merged result. |
| `final_verification` | Final PASS state and the full merged verification evidence. |

Each task record uses the following fields:

```text
id, parent: "controller", role, model, reasoning_effort, base_sha,
depends_on, writes, owned_paths, forbidden_paths, worktree, verify, status,
result, evidence
```

For `status: "complete"`, add a nonempty `result`, nonempty `evidence`, and
an `output_sha256` in `sha256:<64 hex>` form. A completed named executor task also
adds observed runtime evidence:

```json
"runtime": {
  "agent_role": "supergoal_luna_executor",
  "model": "gpt-5.6-luna",
  "reasoning_effort": "xhigh",
  "evidence": ["binding-canary observation or equivalent runtime record"]
}
```

The `runtime` object is evidence of what ran; `role`, `model`, and
`reasoning_effort` at task level are the requested packet contract. Do not
conflate them.

Valid task states are `planned`, `running`, `complete`, `skipped`, and
`blocked`. A complete run requires every task to be accepted as `complete` or
`skipped` (not merely blocked),
`integration.status: "complete"`, a PASS final reviewer, and PASS final
verification. The manifest validator also rejects duplicate IDs, broken/cyclic
dependencies, any overlapping writer paths, repeated writer worktrees, and a
path listed in both a task's owned and forbidden sets.

`parent: "controller"` documents the direct controller-to-task relation in
the manifest. It is not a claim that the platform's hidden topology is
provably flat; an observed runtime canary is required when that distinction
matters.

## Work packet contract

The controller creates one packet per task from the manifest. It must include:

```text
- run ID, task ID, parent=controller, and base SHA
- named role plus requested model and reasoning effort
- one outcome, DAG prerequisites, and success/failure conditions
- task worktree, owned paths, and forbidden paths/actions
- exact verification command(s), expected result, and time/resource limit
- required return: changed files, result, raw output/artifacts,
  output SHA, blockers, and integration notes
- requirement to provide observed runtime evidence when the runtime exposes it
```

For a researcher, `writes` is false, `owned_paths` is empty, `worktree` is
`null`/empty, and the packet must say return-only. For an executor, `writes`
is true only for its assigned worktree and owned paths.
No task writes `.supergoal/`, shared integration files, another task's
worktree, or a forbidden path. A sandbox is helpful defence in depth but
should never be documented as proof that this rule held.

## Scheduling, barriers, and integration

1. **Find ready nodes.** A node is eligible only when all dependencies have
   accepted terminal results and its base SHA identifies the current snapshot
   it was planned against. It can legitimately differ from the run's initial
   top-level `base_sha` after an earlier integration wave.
2. **Choose a bounded wave.** Spawn only independent ready nodes, up to the
   agreed capacity and no more than ten task records in the run. If there are
   more nodes, use waves; if there are fewer, use fewer.
3. **Wait at a barrier.** Wait for selected tasks to become terminal. A
   blocked, stale, out-of-scope, or unverified result is not silently
   converted to complete.
4. **Validate each return.** Compare base SHA, changed paths, task result,
   verify output, output hash, and observed runtime object to the manifest.
   Reject a mismatched result and replan it.
5. **Integrate centrally.** The controller integrates accepted results in
   topological order. It owns conflicts, shared/lock/generated files, and
   updates the base SHA after each merge.
6. **Recompute readiness.** A downstream task whose base SHA is stale is
   rebased or replanned; it is not merged on faith.
7. **Verify and review.** Run the complete verification surface against the
   merged state, persist integration/final evidence, and send that state to a
   fresh reviewer. Only then may phase become `complete`.

The controller may execute a serial node itself when delegation would add
overhead or create a conflict. This is a successful adaptive decision, not a
failure to use agents.

## Runtime binding canary

Before relying on named executor execution as a strong guarantee, run a small
canary and preserve its observation separately from the manifest. The shipped
audit accepts an explicit observation such as (the values shown are the
shipped `[executor]` defaults):

```json
{
  "executors": [
    {
      "id": "T1",
      "agent_role": "supergoal_luna_executor",
      "requested_model": "gpt-5.6-luna",
      "requested_reasoning_effort": "xhigh",
      "model": "gpt-5.6-luna",
      "reasoning_effort": "xhigh",
      "evidence": ["runtime observation"]
    }
  ]
}
```

Use `manifest_audit.py --binding-canary <observation.json>` when installed.
It validates that observed model and effort equal the declared requested values,
without parsing private SQLite or rollout records. A passing canary is evidence
for the observed runtime and surface only; it does not prove every future
session will bind identically.

## Local version-pinned v2 experiment

The adaptive workflow is the default. This v2 profile is local,
version-pinned compatibility material, not a public portable setup:

1. Pin the Codex version and explicitly enable v2 only after confirming the
   keys work on that exact surface. Use only the v2 session capacity setting;
   do not also set `agents.max_threads`. Do not derive a worker count from it.
2. Invoke named children with `fork_turns="none"` and expose spawn metadata
   only where that exact build supports them.
3. Run a binding/topology canary before relying on the profile. Record role,
   model, effort, parent, timing, and actual worker count.
4. Do not promise exact N under Sol/Ultra. Ultra may delegate proactively,
   and a depth setting does not provide a complete no-descendant guarantee.
   Capacity limits, explicit packets, and post-run observations are only
   compensating controls.
5. For a hard guarantee of one manager plus exactly N specified workers across
   surfaces, use separate explicitly configured Codex sessions or an Agents
   SDK orchestrator. `/goal` and a role card alone cannot provide it.

## Resume and migration

Resume from `BRIEF.md`, `PLAN.md`, `run_manifest.json`, and the journal tail.
The manifest phase tells the controller whether to replan, execute, integrate,
or close. A task with an old base SHA is stale; a terminal task missing its
required evidence is not accepted.

Legacy missions without a version-1 manifest do not receive a retroactive
completion claim. Preserve their human evidence, create a new plan-phase
manifest from the current snapshot, validate a fresh DAG, and execute only the
remaining work under this contract.
