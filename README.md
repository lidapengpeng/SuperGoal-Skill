<div align="center">

# SuperGoal

**A plan-first Codex skill for durable objectives, bounded delegation, merged verification, and fresh review.**

![Codex CLI skill](https://img.shields.io/badge/Codex%20CLI-skill-111827?style=flat-square)
![Adaptive DAG](https://img.shields.io/badge/execution-adaptive%20DAG-2563eb?style=flat-square)
![Evidence gated](https://img.shields.io/badge/evidence-gated-22c55e?style=flat-square)
![Fresh review](https://img.shields.io/badge/review-fresh%20context-8b5cf6?style=flat-square)

<code>$supergoal &lt;task&gt;</code> -> recon -> contract -> plan -> bounded work -> integration -> verified close

<sub>English | <a href="README.zh-CN.md">中文</a></sub>

</div>

---

SuperGoal is a local Codex skill for work that should not be called complete
without evidence. It uses <code>/goal</code> for the durable objective and
stopping condition, then adds the operational controls <code>/goal</code> does
not itself supply: a repository-aware plan, explicit task ownership,
controller-owned integration, and fresh review of the merged result.

Use it for multi-step engineering work, risky changes, migrations, data
pipelines, experiments, or refactors with a meaningful verification surface.
Skip it for a one-line answer or a loose, unrelated backlog.

## Current workflow

~~~mermaid
flowchart TD
  A["$supergoal &lt;task&gt;"] --> B["Recon repository and constraints"]
  B --> C["Clarify only unresolved intent\nsuccess criterion + budget"]
  C --> D["Agree one contract"]
  D --> E["Create /goal + plan-phase run_manifest.json"]
  E --> F["Controller validates a dependency DAG"]
  F --> G{"Material uncertainty?"}
  G -->|yes| H["Optional read-only research task\nonly if evidence changes the plan"]
  G -->|no| I["Fresh plan review"]
  H --> I
  I --> J{"Independent ready work?"}
  J -->|none| K["Controller performs serial work"]
  J -->|yes| L["Bounded executor records\nunique worktrees + path contracts"]
  K --> M["Controller integrates and verifies"]
  L --> N["Wait for terminal results\nvalidate scope, base, and evidence"]
  N --> M
  M --> O["Fresh final review"]
  O -->|PASS| P["Close with retained evidence"]
  O -->|FAIL or CANNOT-VERIFY| F
~~~

The controller may create **zero through ten direct manifest task records in
total**. That ceiling includes read-only research tasks and write executor
tasks; it is not ten executors plus research. A small deterministic task can
have no delegated record at all. A larger DAG can use bounded waves rather than
inventing filler work.

| Control | Current contract |
| --- | --- |
| Planning | Controller creates and validates the DAG before delegation; a fresh reviewer attacks it. |
| Delegation | Only independent, owned work is delegated. Each writer gets a distinct worktree and path boundary. |
| Research | Optional. Use it only when an unresolved fact can change a design, risk treatment, or DAG edge. |
| Integration | Controller validates returns, resolves conflicts, integrates in dependency order, and runs the merged verification surface. |
| Completion | A current merged verification result and a fresh reviewer verdict are required before close. |

## Quick start

Requirements: a current Codex client, Git, and Python 3.11 or newer for the
shipped Python utilities.

Install the skill bundle locally:

~~~bash
git clone https://github.com/lidapengpeng/SuperGoal-Skill.git ~/.codex/skills/supergoal
~~~

In a target Git repository, invoke it explicitly:

~~~text
$supergoal <task with a concrete outcome and verification condition>
~~~

If <code>/goal</code> is absent, enable Goals first:

~~~bash
codex features enable goals
~~~

Goals are a persisted objective/continuation feature. SuperGoal treats that as
the durable control loop, not as proof that Codex planned, spawned a particular
role, or selected a requested model.

### What Setup installs

Cloning the skill does not automatically modify a target project or an active
Codex session. During Setup, merge the generated assets into the scope you
intend to use, preserving unrelated configuration.

| Asset | Target scope | Purpose |
| --- | --- | --- |
| Skill bundle | <code>~/.codex/skills/supergoal/</code> or <code>&lt;repo&gt;/.codex/skills/supergoal/</code> | The skill, workflow references, source profile, hooks, and tests. |
| Custom-agent cards | <code>~/.codex/agents/</code> or <code>&lt;repo&gt;/.codex/agents/</code> | <code>supergoal_luna_executor</code>, <code>supergoal_researcher</code>, and <code>supergoal_reviewer</code>. |
| Controller config | <code>~/.codex/config.toml</code> or <code>&lt;repo&gt;/.codex/config.toml</code> | Merge the selected controller snippet; do not overwrite an existing config file. |
| Hooks | <code>&lt;repo&gt;/.codex/hooks.json</code> plus copied hook scripts | Completion audit and namespaced subagent-scope advisories. |

The precise file mapping and non-destructive merge rules are in
[references/codex.md](references/codex.md).

## Practical examples

### A serial, zero-worker fix

~~~text
$supergoal Correct the typo in docs/quickstart.md. Verify with git diff --check.
~~~

After recon, the controller can record that no external fact or independent
workstream is needed, keep <code>tasks</code> empty, make the small change
itself, run the verification command, and obtain the compact fresh review. No
research task or executor is created just to satisfy a quota.

### Two bounded independent workstreams

~~~text
$supergoal Update independent component A and component B to use the new header.
Verify each component with its repository-provided targeted test, then run the
merged verification suite.
~~~

Only if recon confirms disjoint ownership and no dependency, the controller
can plan two direct executor records:

~~~text
T1  supergoal_luna_executor  owns <component-A paths>  verify: <A test command>
T2  supergoal_luna_executor  owns <component-B paths>  verify: <B test command>
~~~

Each task receives a base snapshot, one worktree, allowed and forbidden paths,
and an evidence requirement. The controller waits for terminal results,
rejects stale or out-of-scope returns, integrates accepted work, then verifies
and reviews the combined state. If current external information would change
this plan, one <code>supergoal_researcher</code> record may be added - and it
consumes one of the same ten total record slots.

## Roles and model profile

The named role is an identifier and behavior contract; it is not proof of the
model that ultimately ran.

| Role | Default requested runtime | Responsibility |
| --- | --- | --- |
| Controller | Sol / <code>ultra</code> | Recon, planning, task packets, integration, user communication, and final decision flow. |
| <code>supergoal_luna_executor</code> | Luna / <code>xhigh</code> | One bounded write task in its assigned worktree. |
| <code>supergoal_researcher</code> | Luna / <code>xhigh</code> | One optional, read-only evidence question. |
| <code>supergoal_reviewer</code> | Sol / <code>max</code> | Fresh plan, subgoal, and final attack on unsupported claims. |

Edit [config/model-profile.toml](config/model-profile.toml) to change the
shipped defaults in one place. It synchronizes two controller snippets and the
three role cards; it does not alter an already-running session, deployed
<code>.codex</code> files, or task fields in an existing manifest.

For example, make executor work use Terra with high reasoning:

~~~toml
[executor]
model = "gpt-5.6-terra"
reasoning_effort = "high"
~~~

Then regenerate, check the local model catalog, and redeploy the resulting
cards/snippet through Setup:

~~~bash
python3 hooks/sync_model_profile.py --write
python3 hooks/sync_model_profile.py --check --catalog-check
~~~

<code>--check</code> detects drift among the shipped generated assets.
<code>--catalog-check</code> asks the active CLI which model/effort pairs it
supports. Model availability and the highest available effort are account- and
surface-dependent, so this check is preferable to assuming a profile value is
runnable everywhere.

There is deliberately no <code>[discussor]</code> section:
<code>supergoal_reviewer</code> owns plan critique and final review. The
synchronizer rejects <code>[discussor]</code> rather than silently accepting an
inactive setting.

## Manifest and evidence

<code>.supergoal/run_manifest.json</code> is the machine-readable execution
contract. It records the plan review, optional research decision, zero through
ten direct task records, integration, final review, and final verification.

Every completed delegated task, including a completed researcher task, needs:

- requested role, model, and reasoning effort;
- result, retained evidence, and output hash;
- an observed runtime object whose role/model/effort match the request.

The controller runtime record and reviewer evidence are separate from task
runtime evidence. The shipped
[run-manifest.example.json](references/run-manifest.example.json) is a
schema-valid **illustrative fixture** with placeholder identities and results.
It is not a live canary or evidence that a named role bound successfully.

Validate the fixture from this checkout with:

~~~bash
python3 hooks/manifest_audit.py --manifest references/run-manifest.example.json
python3 hooks/stop_audit.py --check-manifest --manifest references/run-manifest.example.json
~~~

## Current verification status and limits

| Claim | Status in this repository |
| --- | --- |
| Profile, generated cards, manifest schema, and hook checks | Locally validated by the shipped tests and sample audit. |
| Default Sol/Luna model-effort pairs | Accepted by the local Codex 0.144.0 catalog at the time of validation. Recheck on the active account/surface. |
| Native <code>supergoal_luna_executor</code> binding | **UNPROVEN** on the recorded local Codex CLI 0.144.0 canary: the router returned <code>unknown agent_type</code> and no child was created. |
| Local v2 configuration | Experimental compatibility material, not a recommended or production-validated setup. |

The recorded binding failure is retained in
[docs/canary-20260709-luna-binding.md](docs/canary-20260709-luna-binding.md).
Run a fresh same-surface canary before asserting that a named child used the
requested role, model, or effort. Until then, use an explicitly configured
session or an Agents SDK orchestrator when that separation is a hard
requirement.

Other boundaries matter too:

- <code>/goal</code> persists the objective and stopping condition; it does
  not by itself enforce a plan, fan-out count, role selection, or final
  verification.
- <code>agents.max_threads = 10</code> caps spawned child threads in the
  current 0.144 implementation, while <code>max_depth = 1</code> is the
  direct-child nesting limit. They are capacity controls, not evidence that a
  particular topology occurred.
- Custom-agent card sandbox settings are defaults. A parent's live approval or
  sandbox selection can be reapplied to child sessions.
- Sol Ultra can delegate proactively. Do not infer an exact worker count from
  capacity settings or claim a hard hierarchy across every Codex surface.
- <code>config/config.v2-strict.toml.snippet</code> is retained only for a
  version-pinned local experiment. Its v2 keys are not part of the public
  configuration reference, and the recorded named-role canary did not pass.

For the detailed acceptance measurements, see
[docs/field-validation.md](docs/field-validation.md). For the complete
execution contract, see
[references/super-agent-cluster.md](references/super-agent-cluster.md).

## Official Codex references

- [Goals](https://developers.openai.com/codex/use-cases/follow-goals/)
- [Subagents and custom agents](https://developers.openai.com/codex/multi-agent/)
- [Models and reasoning effort](https://developers.openai.com/codex/models/)
- [Configuration reference](https://developers.openai.com/codex/config-reference/)
