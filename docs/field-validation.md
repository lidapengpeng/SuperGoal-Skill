# Field-validation checklist

Everything in this plugin has been validated structurally (parses, hook
self-tests, end-to-end hook runs, doc consistency) but not behaviorally: no
live Codex mission has exercised it yet. These are the nine questions that
argument cannot settle - each maps to the decision its measurement makes.
Run them during the first three real missions and record the outcomes here.

**Priority first:** FV1, FV3, and FV9 decide whether the control surface is
real. Run those before adding more process. FV5 decides whether
`synthesizer` earns its call (keep until measured; fold only on the rule
below).

| # | Measurement | Decides |
| --- | --- | --- |
| FV1 | Capture one live SubagentStop payload; run one deliberate out-of-scope write by a bulk-writer agent | Hook blocks -> drop the per-wave `--audit` duty from scheduler duties (keep `--snapshot`). Payload never matches -> drop the hooks.json SubagentStop entry; `--audit` becomes the sole net. |
| FV2 | Does `stop_hook_active` appear in live Stop events, and does the one-nudge cycle behave (block once, pass second)? | Whether the Stop hook's no-loop guarantee is real, or a sentinel-file fallback (`.supergoal/tmp/.stop-nudged`) is needed. |
| FV3 | Set `max_threads = 1` and observe whether the 4-wide debate serializes | Whether the `[agents]` config keys are real platform enforcement or fictional (TOML parsers ignore unknown tables silently). |
| FV4 | Count refuted cycles / hard-rule-4 events / reopens whose root lacks an `L-` entry in PROJECT.md at Close | Slippage over ~1/3 justifies a minimal Stop-hook check for lessons consolidation; below that, discipline suffices. |
| FV5 | Per REVISE round: gate decisions that overrode the synthesis, and rejected objections reviewers re-raised next round | Rubber-stamp + no-resurface -> merge `synthesizer` into the main thread; divergence -> its isolation earns the call. **Default until measured: keep `synthesizer`.** |
| FV6 | On a monorepo survey-tier mission: tier or contract errors that a longer explorer return would have contained | Whether `explorer`'s flat 40-line bound needs a per-mode variant. |
| FV7 | Sources actually needed per fix-mode question | Calibrate the 5-15 band in `config/researcher.toml`. |
| FV8 | Wall-clock and context size of one survey researcher call (30-60 sources) | The split threshold for per-approach-family calls. |
| FV9 | At Setup, can the session actually enumerate configured MCP servers (`/mcp`) and installed sibling skills (the skills directories)? | Whether the tooling inventory (Setup step 4) and its routing map are live behavior or need a user-supplied inventory line at Clarify. |

## Runnable steps (FV1, FV3, FV9)

Live Codex is required. Structural self-tests do not answer these.

### FV1 — SubagentStop write-scope hook

1. Open a standard-tier mission past Agree so `.supergoal/` exists.
2. Before spawning `designer`, run:
   `python <repo>/.codex/hooks/subagent_audit.py --snapshot`
3. Spawn `designer` with a packet that deliberately also writes
   `.supergoal/RESEARCH.md` (out of scope).
4. Capture the SubagentStop stdin payload (Codex hook log / debug) and the
   hook stdout.
5. Record: payload keys that identify the agent; whether
   `{"decision":"block",...}` appeared; whether `--audit designer` alone
   would have caught the same plant.
6. Decision rule: see table row FV1.

### FV3 — `max_threads` enforcement

1. In the active Codex config, set `[agents] max_threads = 1` (snippet in
   `config/config.toml.snippet`).
2. Run one debate round that schedules all four reviewers in one wave.
3. Observe wall-clock overlap: four near-simultaneous starts vs strict
   serial turns.
4. Decision rule: serial under `max_threads = 1` -> keys are real; still
   parallel -> treat `max_threads` as documentation only and assume
   correlated reviewers until proven otherwise.

### FV9 — Setup tooling inventory

1. On a machine with at least one MCP server configured and one sibling
   skill installed, invoke `$supergoal` Setup.
2. Check whether Setup step 4 can list `/mcp` servers and skill directories
   without the user pasting an inventory.
3. If enumeration fails or is empty when tools exist: add a Clarify line
   "tooling inventory (user-supplied)" and stop treating Setup discovery
   as authoritative.
4. Decision rule: see table row FV9.

### FV5 — synthesizer keep / fold (record during REVISE rounds)

Keep `synthesizer` until this measurement completes. Per REVISE round log:

- Did the main-thread gate decision match the synthesis recommendation?
- Did any rejected objection resurface in the next round with the same
  root tag?

**Fold into main thread** only when, across ≥3 REVISE rounds in real
missions: gate never overrides synthesis **and** rejected objections never
resurface. **Keep** on any divergence (override or resurface) — isolation
is earning the call.

## Outcomes

(append dated entries as missions answer these)
