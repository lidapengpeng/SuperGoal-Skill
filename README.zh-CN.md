<div align="center">

# SuperGoal

**面向 Codex 的计划优先技能：持久目标、有界委派、合并验证与独立复核。**

![Codex CLI skill](https://img.shields.io/badge/Codex%20CLI-skill-111827?style=flat-square)
![Adaptive DAG](https://img.shields.io/badge/execution-adaptive%20DAG-2563eb?style=flat-square)
![Evidence gated](https://img.shields.io/badge/evidence-gated-22c55e?style=flat-square)
![Fresh review](https://img.shields.io/badge/review-fresh%20context-8b5cf6?style=flat-square)

<code>$supergoal &lt;task&gt;</code> -> 侦察 -> 契约 -> 计划 -> 有界执行 -> 集成 -> 验证关闭

<sub><a href="README.md">English</a> | 中文</sub>

</div>

---

SuperGoal 是一个本地 Codex 技能，适用于没有证据就不应被称为“完成”的工作。
它使用 <code>/goal</code> 保存持久目标和停止条件，并补上 <code>/goal</code>
本身不提供的运行控制：了解仓库的计划、明确的任务所有权、由 controller
负责的集成，以及对合并结果的独立复核。

适合多步骤工程工作、高风险修改、迁移、数据管道、实验，或具有重要验证面的
重构。不适合一句话回答或松散且互不相关的待办清单。

## 当前工作流

~~~mermaid
flowchart TD
  A["$supergoal <task>"] --> B["侦察仓库和约束"]
  B --> C["只澄清尚未确定的意图\n成功标准 + 预算"]
  C --> D["确认一份契约"]
  D --> E["创建 /goal + 计划阶段 run_manifest.json"]
  E --> F["Controller 验证依赖 DAG"]
  F --> G{"是否存在实质性不确定性？"}
  G -->|是| H["可选的只读研究任务\n仅在证据会改变计划时使用"]
  G -->|否| I["独立的计划复核"]
  H --> I
  I --> J{"是否有独立的就绪工作？"}
  J -->|没有| K["Controller 串行执行"]
  J -->|有| L["有界的 executor 记录\n独立 worktree + 路径契约"]
  K --> M["Controller 集成并验证"]
  L --> N["等待终态结果\n验证范围、基线和证据"]
  N --> M
  M --> O["独立的最终复核"]
  O -->|PASS| P["保留证据后关闭"]
  O -->|FAIL 或 CANNOT-VERIFY| F
~~~

Controller 最多可创建**零到十条直属 manifest 任务记录，总数合计**。该上限包含
只读研究任务和写入 executor 任务；并非“十个 executor 再加研究”。一个确定性
的小任务可以完全没有委派记录。较大的 DAG 可以分有界波次运行，而不是虚构
填充工作。

| 控制项 | 当前契约 |
| --- | --- |
| 计划 | Controller 在委派前创建并验证 DAG；独立 reviewer 对其进行审查。 |
| 委派 | 只委派独立且所有权明确的工作。每个写入任务都有不同的 worktree 和路径边界。 |
| 研究 | 可选。仅当未解决的事实会改变设计、风险处理或 DAG 边时使用。 |
| 集成 | Controller 验证返回结果、解决冲突、按依赖顺序集成，并运行合并后的验证面。 |
| 完成 | 关闭前必须有当前合并状态的验证结果和独立 reviewer verdict。 |

## 快速开始

要求：当前版本的 Codex 客户端、Git，以及用于随附 Python 工具的 Python 3.11
或更高版本。

将技能包安装到本机：

~~~bash
git clone https://github.com/lidapengpeng/SuperGoal-Skill.git ~/.codex/skills/supergoal
~~~

在目标 Git 仓库中显式调用：

~~~text
$supergoal <task with a concrete outcome and verification condition>
~~~

如果没有 <code>/goal</code>，请先启用 Goals：

~~~bash
codex features enable goals
~~~

Goals 是持久化目标/持续执行功能。SuperGoal 将其作为持久控制循环，而不把它
视为 Codex 已完成计划、生成某个特定角色或选择请求模型的证据。

### Setup 安装哪些内容

克隆技能不会自动修改目标项目或正在运行的 Codex 会话。在 Setup 期间，请将
生成的资源合并到你打算使用的作用域，并保留无关配置。

| 资源 | 目标作用域 | 用途 |
| --- | --- | --- |
| 技能包 | <code>~/.codex/skills/supergoal/</code> 或 <code>&lt;repo&gt;/.codex/skills/supergoal/</code> | 技能、工作流参考、源 profile、hooks 和测试。 |
| 自定义 agent 卡片 | <code>~/.codex/agents/</code> 或 <code>&lt;repo&gt;/.codex/agents/</code> | <code>supergoal_luna_executor</code>、<code>supergoal_researcher</code> 和 <code>supergoal_reviewer</code>。 |
| Controller 配置 | <code>~/.codex/config.toml</code> 或 <code>&lt;repo&gt;/.codex/config.toml</code> | 合并所选 controller snippet；不要覆盖已有配置文件。 |
| Hooks | <code>&lt;repo&gt;/.codex/hooks.json</code> 加上复制的 hook 脚本 | 完成审计及带命名空间的 subagent 作用域 advisory。 |

精确的文件映射和非破坏性合并规则见
[references/codex.md](references/codex.md)。

## 实用示例

### 串行、零 worker 的小修复

~~~text
$supergoal Correct the typo in docs/quickstart.md. Verify with git diff --check.
~~~

完成侦察后，controller 可以记录无需外部事实或独立工作流，保持
<code>tasks</code> 为空，自行完成这个小修改，运行验证命令，并获得精简的独立
复核。不会为了满足配额而创建研究任务或 executor。

### 两个有界且相互独立的工作流

~~~text
$supergoal Update independent component A and component B to use the new header.
Verify each component with its repository-provided targeted test, then run the
merged verification suite.
~~~

只有在侦察确认所有权互不重叠且没有依赖关系时，controller 才能规划两条直属
executor 记录：

~~~text
T1  supergoal_luna_executor  owns <component-A paths>  verify: <A test command>
T2  supergoal_luna_executor  owns <component-B paths>  verify: <B test command>
~~~

每项任务都会收到基线快照、一个 worktree、允许和禁止的路径，以及证据要求。
Controller 等待终态结果，拒绝过期或超出范围的返回，集成被接受的工作，随后验证
并复核组合后的状态。如果当前外部信息会改变该计划，可以添加一条
<code>supergoal_researcher</code> 记录——它同样占用十条记录总上限中的一个位置。

## 角色和模型 profile

具名角色是标识符和行为契约；它不是最终实际运行模型的证据。

| 角色 | 默认请求的运行时 | 职责 |
| --- | --- | --- |
| Controller | Sol / <code>ultra</code> | 侦察、计划、任务包、集成、用户沟通和最终决策流程。 |
| <code>supergoal_luna_executor</code> | Luna / <code>xhigh</code> | 在其分配的 worktree 中完成一个有界写入任务。 |
| <code>supergoal_researcher</code> | Luna / <code>xhigh</code> | 完成一个可选的只读证据问题。 |
| <code>supergoal_reviewer</code> | Sol / <code>max</code> | 对计划、子目标和缺少支撑的完成声明进行独立审查。 |

编辑 [config/model-profile.toml](config/model-profile.toml)，即可在一个位置修改
随附资源的默认值。它会同步两份 controller snippet 和三张角色卡片；不会修改
已经运行的会话、已部署的 <code>.codex</code> 文件，或现有 manifest 中的任务字段。

例如，让 executor 工作使用 Terra 和 high reasoning：

~~~toml
[executor]
model = "gpt-5.6-terra"
reasoning_effort = "high"
~~~

随后重新生成、检查本地模型目录，并通过 Setup 重新部署生成的卡片/snippet：

~~~bash
python3 hooks/sync_model_profile.py --write
python3 hooks/sync_model_profile.py --check --catalog-check
~~~

<code>--check</code> 会检测随附生成资源之间的漂移。
<code>--catalog-check</code> 会询问当前 CLI 支持哪些 model/effort 组合。模型可用性
和最高可用 effort 会因账户和运行 surface 而异，因此应使用此检查，而不是假定
某个 profile 值处处都能运行。

这里有意没有 <code>[discussor]</code> section：
<code>supergoal_reviewer</code> 负责计划批评和最终复核。同步器会拒绝
<code>[discussor]</code>，而不是静默接受一个不会生效的设置。

## Manifest 与证据

<code>.supergoal/run_manifest.json</code> 是机器可读的执行契约。它记录计划复核、
可选研究决策、零到十条直属任务记录、集成、最终复核和最终验证。

每一条已完成的委派任务（包括已完成的 researcher 任务）都需要：

- 请求的角色、模型和 reasoning effort；
- 结果、保留的证据和输出 hash；
- 一个观测到的 runtime 对象，其角色/模型/effort 与请求相匹配。

Controller runtime 记录和 reviewer 证据与任务 runtime 证据是分开的。随附的
[run-manifest.example.json](references/run-manifest.example.json) 是一个
schema-valid 的**示例 fixture**，其中的身份和结果均为占位内容。它不是实时
canary，也不是某个具名角色绑定成功的证据。

从此 checkout 运行以下命令即可验证该 fixture：

~~~bash
python3 hooks/manifest_audit.py --manifest references/run-manifest.example.json
python3 hooks/stop_audit.py --check-manifest --manifest references/run-manifest.example.json
~~~

## 当前验证状态与限制

| 声明 | 本仓库中的状态 |
| --- | --- |
| Profile、生成的卡片、manifest schema 和 hook 检查 | 已由随附测试和 sample audit 在本地验证。 |
| 默认 Sol/Luna model-effort 组合 | 在验证时被本地 Codex 0.144.0 catalog 接受。请在当前账户/surface 上重新检查。 |
| 原生 <code>supergoal_luna_executor</code> 绑定 | 在记录的本地 Codex CLI 0.144.0 canary 上为 **UNPROVEN**：router 返回 <code>unknown agent_type</code>，且没有创建 child。 |
| 本地 v2 配置 | 实验性的兼容性材料，不是推荐设置，也未经生产验证。 |

记录的绑定失败保留在
[docs/canary-20260709-luna-binding.md](docs/canary-20260709-luna-binding.md)。
在声称具名 child 使用了请求的角色、模型或 effort 前，请重新运行同一 surface
上的 canary。在此之前，如果这种分离是硬性要求，请使用显式配置的 session 或
Agents SDK orchestrator。

其他边界也很重要：

- <code>/goal</code> 保存目标和停止条件；它本身不会强制计划、fan-out 数量、角色
  选择或最终验证。
- <code>agents.max_threads = 10</code> 在当前 0.144 实现中限制生成的 child threads，
  而 <code>max_depth = 1</code> 是直属 child 的嵌套上限。它们是容量控制，不是某个
  特定拓扑实际发生过的证据。
- 自定义 agent 卡片中的 sandbox 设置只是默认值。父级实时 approval 或 sandbox
  选择可以重新应用到 child session。
- Sol Ultra 可以主动委派。不要根据容量设置推断精确 worker 数量，也不要声称在
  每一种 Codex surface 上都有硬层级。
- <code>config/config.v2-strict.toml.snippet</code> 仅为版本固定的本地实验而保留。
  其 v2 keys 不属于公开配置参考，且记录的具名角色 canary 未通过。

详细的验收测量见
[docs/field-validation.md](docs/field-validation.md)。完整执行契约见
[references/super-agent-cluster.md](references/super-agent-cluster.md)。

## 官方 Codex 参考资料

- [Goals](https://developers.openai.com/codex/use-cases/follow-goals/)
- [Subagents and custom agents](https://developers.openai.com/codex/multi-agent/)
- [Models and reasoning effort](https://developers.openai.com/codex/models/)
- [Configuration reference](https://developers.openai.com/codex/config-reference/)
