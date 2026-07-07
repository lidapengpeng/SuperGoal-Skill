# Field-validation checklist

Everything in this plugin has been validated structurally (parses, hook
self-tests, end-to-end hook runs, doc consistency) but not behaviorally: no
live Codex mission has exercised it yet. These are the nine questions that
argument cannot settle - each maps to the decision its measurement makes.
Run them during the first three real missions and record the outcomes here.

| # | Measurement | Decides |
| --- | --- | --- |
| FV1 | Capture one live SubagentStop payload; run one deliberate out-of-scope write by a bulk-writer agent | Hook blocks -> drop the per-wave `--audit` duty from scheduler duties (keep `--snapshot`). Payload never matches -> drop the hooks.json SubagentStop entry; `--audit` becomes the sole net. |
| FV2 | Does `stop_hook_active` appear in live Stop events, and does the one-nudge cycle behave (block once, pass second)? | Whether the Stop hook's no-loop guarantee is real, or a sentinel-file fallback (`.supergoal/tmp/.stop-nudged`) is needed. |
| FV3 | Set `max_threads = 1` and observe whether the 4-wide debate serializes | Whether the `[agents]` config keys are real platform enforcement or fictional (TOML parsers ignore unknown tables silently). |
| FV4 | Count refuted cycles / hard-rule-4 events / reopens whose root lacks an `L-` entry in PROJECT.md at Close | Slippage over ~1/3 justifies a minimal Stop-hook check for lessons consolidation; below that, discipline suffices. |
| FV5 | Per REVISE round: gate decisions that overrode the synthesis, and rejected objections reviewers re-raised next round | Rubber-stamp + no-resurface -> merge `synthesizer` into the main thread; divergence -> its isolation earns the call. |
| FV6 | On a monorepo survey-tier mission: tier or DRAFT_BRIEF errors that a longer explorer return would have contained | Whether `explorer`'s flat 40-line bound needs a per-mode variant. |
| FV7 | Sources actually needed per fix-mode question | Calibrate the 5-15 band in `config/researcher.toml`. |
| FV8 | Wall-clock and context size of one survey researcher call (30-60 sources) | The split threshold for per-approach-family calls. |
| FV9 | At Setup, can the session actually enumerate configured MCP servers (`/mcp`) and installed sibling skills (the skills directories)? | Whether the tooling inventory (Setup step 4) and its routing map are live behavior or need a user-supplied inventory line at Clarify. |

## Outcomes

(append dated entries as missions answer these)
