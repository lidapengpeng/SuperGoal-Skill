# Observed Luna role-binding canary — 2026-07-09

## Purpose

Test whether this local Codex CLI surface can create one direct
`supergoal_luna_executor` child with its requested `gpt-5.6-luna` / `xhigh`
runtime. The child was instructed to return a fixed string only; no generic
fallback was allowed.

## Environment

- CLI: `codex-cli 0.144.0`
- Isolated temporary Git repository
- Project card: `.codex/agents/supergoal_luna_executor.toml`
- Root request: `gpt-5.6-sol` / `ultra`
- v2: enabled, `max_concurrent_threads_per_session = 2`,
  `hide_spawn_agent_metadata = false`
- Spawn request: `agent_type="supergoal_luna_executor"`,
  `fork_turns="none"`
- Sandbox: read-only

## Observations

Two runs used the same project-local card and spawn request:

| Run | Result |
| --- | --- |
| Ephemeral CLI session | Router returned `unknown agent_type 'supergoal_luna_executor'`. No child was created. |
| Persisted CLI session | Router returned the same `unknown agent_type 'supergoal_luna_executor'`. No child was created. |

No generic fallback child was spawned. Therefore the child role, model,
reasoning effort, and response are all **UNVERIFIED**.

## Decision

Do not claim native named-Luna binding for this tested `codex-cli 0.144.0`
surface. Use an explicitly configured Luna session or an Agents SDK
orchestrator until an upgraded same-surface canary succeeds.
