# Codex machinery (Setup phase)

Everything in this file is platform glue for Codex CLI. SuperGoal is a Codex
skill, so `/goal`, the Stop hook, custom agents, and strong-model config are
required Setup wiring. The `.supergoal/` state files provide the evidence ledger;
the Codex wiring makes the ledger enforceable.

## /goal - one durable goal per mission

`/goal` attaches one durable objective to the thread; Codex keeps working
toward it across turns and may only mark it complete when evidence supports
completion. SuperGoal requires `[features] goals = true` (Codex >= 0.128);
check with `/goal`, enable with `codex features enable goals` or merge the
snippet in `config/config.toml.snippet`.

Why one top-level goal, not many small ones: a goal is thread-scoped state -
one thread holds one goal. Splitting a mission into a chain of small `/goal`
commands destroys the global verification surface; each fragment can be
"achieved" shallowly while the mission fails. Instead: one `/goal` whose
completion condition references `.supergoal/PLAN.md`; subgoals live in the
plan, each with its own verify command.

Template (fill from the confirmed Agree message - every element maps 1:1):

```text
/goal <outcome> verified by <verification surface: exact commands, metrics,
artifacts> while preserving <constraints that must not regress>. Use
<boundaries: allowed files, tools, data; protected paths>. Between
iterations, follow the DAOR discipline in .supergoal/: pick the single
highest-value unchecked subgoal from PLAN.md, log every cycle to JOURNAL.md,
and mark a subgoal done only after its verify command passes and the
adversarial reviewer returns PASS. Budget: at most <N> DAOR cycles
[ML: and <H> GPU-hours / <M> full training runs]; stop and report when
exhausted. If blocked or no valid paths remain, stop with: attempted paths,
evidence gathered, the blocker, and the input that would unlock progress.
```

Lifecycle: `/goal` shows status; `/goal pause`, `/goal resume`,
`/goal clear` control it. States: pursuing / paused / achieved / unmet /
budget-limited. Treat "achieved" as a claim, not a fact: the Close audit
still runs. If `/goal` is unavailable, stop at Setup and enable goals before
starting the Loop; do not run SuperGoal as plain instructions.

## Stop hook - mechanical completion audit

`hooks/stop_audit.py` reads the Stop event and blocks session end while
verifiable work remains: unchecked PLAN boxes, checked boxes without their
logged `review: PASS`, a checked FINAL without its `## FINAL GATE` section,
a cluster mission (DESIGN.md present) past Agree without a passed
`## FINAL DESIGN INSPECTION`, PENDING experiment rows. It is a guardrail, not a
verifier - it checks ledger consistency, not scientific validity.

Install automatically during Setup:

1. Copy `hooks/stop_audit.py` to `<repo>/.codex/hooks/stop_audit.py`. Also copy
   `hooks/subagent_audit.py` (the experimental SubagentStop write-scope audit -
   see below).
2. Select the hook command for the platform BEFORE merging: on POSIX shells
   keep the shipped `python3 "$(git rev-parse ...)"` form; on Windows use
   `python` and - when hooks run through `cmd.exe` or the project has no git -
   an absolute path (details below). Installing the POSIX form on native
   Windows is a silent no-op, the exact failure class this project's own hook
   lesson names.
3. Merge `hooks/hooks.json` into `<repo>/.codex/hooks.json` idempotently,
   never destructively: if the file exists, back it up to `hooks.json.bak`
   first; keep every existing hook; append the SuperGoal Stop entry only
   if no existing command mentions `stop_audit.py`, and the SubagentStop entry
   only if none mentions `subagent_audit.py`. Re-running the wiring must change
   nothing.
4. Self-test the installed Stop hook: pipe a synthetic Stop event whose `cwd`
   points at a temp dir containing a known-bad `PLAN.md` (one unchecked box)
   into the installed script and assert it prints a block decision. A Setup
   that cannot demonstrate one real block has not installed an enforcement
   layer - the layer cannot verify its own installation any other way.
5. This skill assumes the target Codex environment trusts project hooks by
   default. If Codex still reports the hook as untrusted or refuses to load it,
   stop Setup and report that the environment is not compatible with this
   SuperGoal profile.

The shipped command is POSIX-oriented:

```json
"command": "python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/stop_audit.py\""
```

On native Windows two things change: `python3` is usually `python`, and
`$(...)` is a POSIX substitution. PowerShell supports `$(...)`
subexpressions and forward-slash paths reach Python fine, so when Codex runs
hooks through PowerShell this variant works:

```json
"command": "python \"$(git rev-parse --show-toplevel)/.codex/hooks/stop_audit.py\""
```

If hooks run through `cmd.exe`, `$(...)` does not expand - wire an absolute
path to `stop_audit.py` instead. Also wire an absolute path when the target
project is not inside a git repository, because the shipped command uses
`git rev-parse --show-toplevel` only to locate the repo root. The script
itself is portable: it walks up from `cwd` and needs no POSIX shell. Without
a compatible command, Setup is blocked. The SubagentStop command below shares
all of these platform rules.

## SubagentStop hook - write-scope enforcement (experimental)

`hooks/subagent_audit.py` fires when a write-capable cluster agent's turn ends
and blocks it if the agent created, modified, or deleted a `.supergoal/` file
outside its declared scope. It pairs with the scheduler: before spawning a
write-capable wave the main thread runs
`python <repo>/.codex/hooks/subagent_audit.py --snapshot`, which records a
SHA-256 per `.supergoal/` file (tmp/ excluded) into
`.supergoal/tmp/.write-audit-baseline`; on the agent's turn end the hook
re-snapshots, diffs, and checks each changed path against the agent's
allow-list (the three bulk writers each own one document; `worker` owns only
`.supergoal/tmp/`). Reviewers never match - they are read-only. The `hooks.json`
entry matches `^(researcher|designer|synthesizer|worker)$`.

Content hashing, not `git status`, on purpose: in the common layout `.supergoal/`
is untracked, so git collapses the whole tree to one `?? .supergoal/` line and a
content edit to an untracked file never changes status output - a diff of
status text misses real violations there. Hashing sees content regardless of
tracking state, and the audit script itself needs no git (the shipped hook
*command* still uses `git rev-parse` only to locate the repo root).

This is experimental: the exact SubagentStop payload shape and the JSON-stdout
requirement were designed from documentation, not verified against a live Codex
install (confirm against `developers.openai.com/codex/hooks` before trusting it
as the primary enforcement path). Every failure mode in the script degrades to
"do not block", so a payload mismatch cannot wedge a session; until it is
verified, the scheduler's `--audit <agent>` run of the same script after each
write-capable wave remains the primary safety net.

## Custom agents

SuperGoal ships ten custom agents. Three run on every mission:
`config/reviewer.toml` (read-only adversarial reviewer for the Gate phase),
`config/explorer.toml` and `config/worker.toml` (which override Codex's
built-in lightweight agents so the skill never falls back to mini models
during exploration or delegated implementation). The other seven run only on
standard/high-risk missions, as the design cluster
(`references/super-agent-cluster.md`): `researcher`, `designer`,
`design-reviewer`, `risk-reviewer`, `verifier`, `leanness-reviewer`,
`synthesizer`. All ten pin `model = "gpt-5.5"` and
`model_reasoning_effort = "xhigh"`; reviewers are `sandbox_mode = "read-only"`,
bulk writers are `workspace-write`.

Install during Setup by copying every `config/*.toml` agent file except
`config.toml.snippet` to `<repo>/.codex/agents/` (all ten; the cluster
agents are a one-time install cost even though small missions never invoke
them at runtime). If the target directory already contains an unrelated
agent under one of these names, stop Setup and report the collision - never
silently replace it:

```text
config/reviewer.toml         -> <repo>/.codex/agents/reviewer.toml
config/explorer.toml         -> <repo>/.codex/agents/explorer.toml
config/worker.toml           -> <repo>/.codex/agents/worker.toml
config/researcher.toml       -> <repo>/.codex/agents/researcher.toml
config/designer.toml         -> <repo>/.codex/agents/designer.toml
config/design-reviewer.toml  -> <repo>/.codex/agents/design-reviewer.toml
config/risk-reviewer.toml    -> <repo>/.codex/agents/risk-reviewer.toml
config/verifier.toml         -> <repo>/.codex/agents/verifier.toml
config/leanness-reviewer.toml-> <repo>/.codex/agents/leanness-reviewer.toml
config/synthesizer.toml      -> <repo>/.codex/agents/synthesizer.toml
```

If subagents are unavailable, Setup is incomplete; do not replace reviewer
gates with self-review.

## Config snippet

`config/config.toml.snippet` - merge idempotently into
`<repo>/.codex/config.toml` during Setup. User-level config may also contain
these keys, but the repo profile should carry the SuperGoal defaults for
portable behavior:

```toml
model = "gpt-5.5"
review_model = "gpt-5.5"
model_reasoning_effort = "xhigh"
plan_mode_reasoning_effort = "xhigh"

[features]
goals = true

[agents]
max_threads = 5
max_depth = 1
```

`max_depth = 1` keeps subagents from spawning subagents; the main thread
stays the only scheduler. `max_threads = 5` covers the cluster's peak
concurrency - the four-reviewer debate plus one margin slot (parallel mode
runs in separate worktrees and threads, consuming no subagent slots); small
missions never approach it.

## Parallel mode (advanced, opt-in)

Go parallel only when ALL hold: subgoals touch disjoint files and share no
training-artifact paths; each subgoal has an independent verify command; the
user explicitly asked for parallel execution.

Mechanics: one git worktree + one Codex thread + one `/goal` per disjoint
subgoal set; define the merge order up front; after each merge the main
thread re-runs the full verification surface before continuing.

## MCP and sibling skills

Prefer configured MCP servers for external truth (official docs, issues,
data systems). Check `/mcp` for what is configured; never invent MCP access.
Setup step 4 inventories both MCP servers and sibling skills
(`~/.codex/skills/`, `<repo>/.codex/skills/`) once per session; the
capability routing map lives in SKILL.md (Subagents, MCP, and sibling
skills). A sibling skill is followed by reading its SKILL.md at the phase it
serves - it is never a callable tool, and it never overrides this skill's
gates.
