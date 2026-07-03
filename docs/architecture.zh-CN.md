# Text Graphics Agent 架构

英文原文：[Text Graphics Agent Architecture](./architecture.md)。

## 核心论点

强多模态模型适合做提案生成器，但不适合直接做账本写入者。这个架构把智能和权力拆开：

```text
MotherAgent
  -> IntentFrame（原始用户语义，只留在母 agent 侧）
  -> Clean TaskSpec（不含原始用户文本）
  -> 一次性专家 agent
  -> AgentProposal 记录
  -> ConstraintChecker
  -> CheckedRecord 账本
  -> ScoreCard
```

母 agent 是调度者和审计者。它可以选择专家、裁剪上下文、拒绝输出，但不能直接提交世界事实或最终产物。

子 agent 是一次性的。它只接收窄化、清洗后的 `TaskSpec`，永远不接收原始用户话语；它产出一个或多个 `AgentProposal` 记录，然后销毁。除非某条检查后的记录接受了它的语义关联，否则这些关联不能变成记忆。

## 记录流

记录流对应 checked-record 管线：

```text
原始观察 / 任务
  -> IntentFrame
  -> 归一化 TaskSpec
  -> 子 agent 提案
  -> 约束检查
  -> accepted/rejected CheckedRecord
  -> 汇总 ScoreCard
```

## 用户语义防火墙

用户语言很有价值，但不是权威来源。用户可能有意或无意地注入错误前提、社交压力、隐藏范围变更或未验证主张。因此平台把原始用户文本视为不可信观察。

```text
原始用户话语
  -> IntentFrame(
       stable_goal,
       atomic_intents,
       user_supplied_claims,
       assumptions,
       contamination_markers
     )
  -> Clean TaskSpec
  -> 一次性子任务
```

规则：

1. 子 agent 可以引用 `user:*` 证据，但它不能是唯一证据。
2. 用户给出的主张在代码、测试、工具或记录验证前，只能保持为主张。
3. 如果原始请求要求绕过审查、跳过测试、直接写事实或悄悄扩大范围，intent frame 必须标记污染，母 agent 必须降低其权威性。
4. 母 agent 可以拆解意图，但不能让拆解后的意图直接成为入账状态。
5. 子 agent 不接收 `raw_text`；它只接收稳定目标、允许范围、锚点和验证要求。
6. 清洗状态不能由调用方自称。`MotherAgent.dispatch()` 只接受 `sanitized=True` 且 `sanitized_provenance="mother_clean_v1"` 的任务，这些任务必须由 `make_clean_task()` 产生。

## 约束族

约束检测模块被实现为可插拔的多态管道。每一个具体的检查规则都继承自 `Constraint` 抽象基类。默认加载 12 个核心防火墙约束（可在 `ConstraintChecker` 初始化时自由装配和自定义）：

1. **信封约束 (`EnvelopeConstraint`)**
   每条记录必须携带 actor、target、cause、result、visibility、source id、scene/scope 和 timestamp。

2. **范围约束 (`ScopeConstraint`)**
   子 agent 只能触碰任务列出的路径或领域。越界是硬拒绝。

3. **权威约束 (`AuthorityConstraint`)**
   提案不能写 committed world facts，不能修改账本，不能发明动作类型，不能绕过审查。

4. **锚点约束 (`AnchorConstraint`)**
   表达必须保留事实包里的必需锚点。候选结果丢失锚点时要拒绝，并回退到模板或默认行为。

5. **证据和测试约束 (`EvidenceConstraint` & `TestConstraint`)**
   提案必须引用证据；实现类任务必须提供测试命令或验证步骤。

6. **用户语义约束 (`ClaimConstraint` & `SanitizedTaskConstraint`)**
   如果全部证据都来自 `user:*`，提案必须拒绝。用户语义可以驱动任务，不能证明任务结果。

7. **生命周期约束**
   每次专家调用都会创建 `ChildSessionRecord`。成功会话以 `destroyed` 结束，失败会话以 `failed` 结束。`ScoreCard` 汇报 `child_sessions` 和 `destroyed_child_ids`。

## Dogfood 第一轮

这个架构第一次用来审查自身时发现了四个真实问题：

1. `TaskSpec.objective` 仍可能复制原始用户语义。
2. `TaskSpec.sanitized` 在母 agent 清洗前默认可信。
3. metadata 泄漏检测只检查一个顶层 key。
4. 子 agent 生命周期身份可能把多个 child id 合并成一个会话。

当前原型通过 intent codes、带 provenance 的 clean task、递归 forbidden metadata-key 扫描，以及每个 child id 一条生命周期记录来修复这些问题。

## 市场调研吸收

原型吸收了当前 agent 框架的结构思路，但不引入运行时依赖：

- LangGraph：显式任务图、ready nodes、以及图执行引擎 `GraphExecutor` 中包含的 checkpoint 和 Fail-Fast 运行思维。
- CrewAI：显式 specialist profiles，而不是把角色文本藏在 prompt 里。
- Microsoft Agent Framework / OpenAI Agents SDK：可脱离聊天 transcript 测试的小型 workflow primitives。

这映射到两个本地模块：

- `profiles.py`：母侧验证子 agent 的角色、范围、工具面、raw-text 访问和持久记忆策略。
- `graph.py`：任务节点、依赖、ready-node 选择、执行 checkpoint 元数据定义，以及负责拓扑驱动的 `GraphExecutor` 运行器（任何节点执行失败或触发 Rejection 违规时立即 Fail-Fast 中止以确保状态安全）。

由于语义污染是主要威胁模型，原型仍拒绝子 agent 持久记忆和子上下文里的原始用户文本。

## 试验 Benchmark

`benchmark.py` 在六个确定性污染场景上对比直接接受 baseline 与母子管线。当前运行包含五个 unsafe 场景和一个 clean 场景：baseline 接受全部五个污染提案；Text Graphics Agent 接受零个污染提案，通过 `ConstraintChecker` 拒绝四个，并在 spawn 前阻断一个 unsafe profile。

这个 benchmark 是闭环协议 sanity check，不是广泛部署声明。它将作为 `docs/paper_draft.zh-CN.md` 的可复现实证表。

## 为什么叫 “Text Graphics”

这里的 “graphics” 指文本向结构化状态的投影：

- 事实变成类型化记录；
- 记录变成可见 UI 或日志；
- UI 截图变成指标观察；
- agent 主张变成 checked records；
- scorecards 变成平台健康状态的可视形状。

这允许多模态母模型利用视觉和语义联想，但不允许这些联想直接写入权威状态。

## 非目标

- 不把自由文本直接解析成世界事实。
- 不给子 agent 持久记忆。
- 不自动创造规则。
- 不访问密钥或账号。
- 暂不和游戏运行时做运营级集成。
