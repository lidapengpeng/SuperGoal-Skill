# Codex machinery (Setup)

This file is the platform glue for SuperGoal. The workflow itself lives in
`SKILL.md` and `references/super-agent-cluster.md`; Codex configuration makes
the requested runtime available but does not turn those requests into proof.

## `/goal`: durable objective, not orchestration

Enable Goals and create one top-level goal per bounded mission. `/goal` keeps
the objective durable across turns and provides a stopping condition. It does
**not** enforce a planning phase, a dependency DAG, a worker count, named-role
binding, model selection, worktree isolation, or final verification.

Use a goal created from the confirmed Agree contract:

```text
/goal <outcome> verified by <commands, metrics, artifacts> while preserving
<constraints>. Work only inside <boundaries>; stop and report when <budget or
blocked condition> occurs. Keep the execution plan and current evidence in
.supergoal/ and do not claim completion without fresh merged verification and
an independent reviewer verdict.
```

The manifest, not the goal prose, records execution state. If `/goal` is not
available, enable it (for example `codex features enable goals`) before
starting a SuperGoal mission; do not silently run the workflow as an
untracked instruction.

## Completion audit hook

Install `hooks/stop_audit.py`, `hooks/manifest_audit.py`, and the experimental
`hooks/subagent_audit.py` during Setup by merging the shipped hook
configuration into `<repo>/.codex/hooks.json`.
Preserve all existing hooks and avoid overwriting an unrelated command. On
POSIX, the shipped command can locate the repository with `git rev-parse`; on
Windows or outside a git checkout, use an appropriate Python executable and
an absolute hook path.

Run the shipped self-tests after installation. From the repository root, the
portable checks are:

```bash
python .codex/hooks/manifest_audit.py --manifest .supergoal/run_manifest.json
python .codex/hooks/stop_audit.py --check-manifest
```

The hook checks that a claimed complete manifest has the required plan review,
terminal tasks, integration, fresh final reviewer, and final verification. It
is a completion **audit**, not a security boundary: Codex's stop-hook protocol
can permit a subsequent stop after a challenge. Treat a challenge as a repair
request, not proof that completion is impossible to bypass.

The audit deliberately consumes `run_manifest.json` rather than private
Codex SQLite tables or transcript parsing. This makes the portable contract
explicit and lets a user retain the evidence with the mission.

The shipped `SubagentStart` and `SubagentStop` entries call
`subagent_audit.py` for the three namespaced roles. It is a post-turn
state-write advisory, not sandbox enforcement: durable `.supergoal` state is
controller-owned, while `.supergoal/tmp/` and `.supergoal/worktrees/` are
excluded task surfaces. Copy the companion script whenever those hook entries
are installed.

## Central model profile

Edit `config/model-profile.toml` to select the requested `model` and
`reasoning_effort` for all workflow roles. Its four sections are
`[controller]`, `[researcher]`, `[executor]`, and `[reviewer]`; it is the
source of truth for both shipped configuration snippets and the three custom
agent cards.

After changing it, apply and check the synchronized files:

```bash
python3 hooks/sync_model_profile.py --write
python3 hooks/sync_model_profile.py --check --catalog-check
```

`--check` reports only source-asset drift; `--catalog-check` verifies the
selected model/effort pair against the active local Codex catalog. Make the
correction in `model-profile.toml`, then rerun `--write`; do not edit model or
effort in the generated plugin files as the primary configuration surface.
After writing, rerun Setup to copy cards and merge the chosen controller
snippet into the active Codex scope. There is no `[discussor]` section or
runtime role: the reviewer owns the plan discussion/critique and the final
review, so use `[reviewer]` to configure that work. `[discussor]` is rejected
rather than silently ignored.

## Custom agents

Install exactly these namespaced cards; do not shadow built-in names such as
`worker` or `explorer`:

```text
config/supergoal_luna_executor.toml -> <repo>/.codex/agents/supergoal_luna_executor.toml
config/supergoal_researcher.toml    -> <repo>/.codex/agents/supergoal_researcher.toml
config/supergoal_reviewer.toml      -> <repo>/.codex/agents/supergoal_reviewer.toml
```

| Card | Profile section | Use |
| --- | --- | --- |
| `supergoal_luna_executor` | `[executor]`, workspace-write | One independent write task with an owned worktree/path packet. |
| `supergoal_researcher` | `[researcher]`, read-only | One optional evidence question. |
| `supergoal_reviewer` | `[reviewer]`, read-only | Fresh plan, subgoal, and final review. |

Stop Setup if a target card name already belongs to an unrelated custom agent;
never silently replace it. Spawn the role by exact name and pass a bounded
packet. The role card supplies defaults, but a live parent sandbox/approval
policy may override a child setting. Therefore the controller records the
requested fields in the task and, for a completed executor task, requires the
manifest `runtime` observation with matching role/model/effort and evidence.

The optional binding canary accepts an explicit observation instead of private
runtime scraping:

```bash
python .codex/hooks/manifest_audit.py --binding-canary observation.json
```

See `references/super-agent-cluster.md` for the observation shape. A passing
canary proves only the observed session/surface; it does not make future
binding cross-version guaranteed.

## Adaptive default profile

Run the model-profile synchronizer first, then merge
`config/config.toml.snippet` into the repository or user Codex config. Its
controller `model` and `model_reasoning_effort` come from `[controller]` in
`config/model-profile.toml`. The remaining adaptive settings cap spawned
agent threads at the same ten-record ceiling used by the manifest:

```toml
[features]
goals = true

[agents]
max_threads = 10
max_depth = 1
```

`max_threads` is a capacity ceiling for spawned agent threads, not a request
to create ten threads. `max_depth = 1` allows direct children while blocking
deeper child spawning in the documented configuration model. Neither setting
proves observed role/model binding or a particular runtime topology. The
controller's DAG, packets, worktree policy, and manifest audit remain the
workflow controls.

## Local, version-pinned v2 experiment

Use the separate
[`config.v2-strict.toml.snippet`](../config/config.v2-strict.toml.snippet)
only when the operator deliberately pins the tested Codex version and owns a
same-surface canary. These v2 keys are retained as local compatibility
material; they are not part of the public configuration reference. It replaces
the adaptive profile, so it cannot accidentally redeclare `[features]` or
coexist with `[agents]`:

```toml
[features.multi_agent_v2]
enabled = true
max_concurrent_threads_per_session = 11 # illustrative local session cap
hide_spawn_agent_metadata = false
```

This replaces the `[agents]` block; do **not** set `agents.max_threads` and
the v2 session cap together. Do not infer an exact worker count from the
sample session-cap value. If the build exposes `fork_turns="none"`, use it
only as a canary condition and record role/model/effort evidence before
treating the profile as usable.

The repository's local 0.144.0 named-role canary failed with `unknown
agent_type`; do not represent this adapter as validated. Do not promise exact
N workers, strict depth, or a hard cross-surface role guarantee. For one
manager plus exactly N specified workers, use separate explicitly configured
Codex sessions or an Agents SDK orchestrator.

## Setup verification

Before executing a real mission, verify:

1. `/goal` is available.
2. The three cards above are installed under their exact names and parse.
3. `python3 hooks/sync_model_profile.py --check --catalog-check` reports no
   source-asset drift and a supported local model/effort pair. Separately
   confirm Setup copied the cards and merged the selected controller snippet
   into the effective Codex configuration.
4. The manifest audit self-test accepts a valid sample and rejects a malformed
   or incomplete completion record.
5. A one-worker executor binding canary records the actual role, model, and
   effort if a strong named-runtime claim will be made.

Configuration or a successful TOML parse is supporting evidence, not runtime
proof. Keep “documented,” “configured,” “observed in this canary,” and
“unproven” separate in both logs and user-facing reports.

## MCP and sibling skills

Inventory configured MCP servers and installed sibling skills once during
Setup. Prefer official documentation, repository evidence, and configured
semantic tools where available; never fabricate tool access. A sibling skill
is read as instructions at the relevant phase, not invoked as a magical
capability, and it does not override the SuperGoal contract.
