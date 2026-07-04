# Text Graphics Agent：面向一次性子 agent 工作流的语义防火墙

英文原文：[Text Graphics Agent: A Semantic Firewall for Disposable Child-Agent Workflows](./paper_draft.md)。

作者：Lijie Wang，独立研究者

联系邮箱：wanglijie100@gmail.com

草稿日期：2026-07-04

Artifact：`text-graphics-agent/`

## 摘要

当前 LLM agent 框架越来越多地支持多 agent 协作、有状态 workflow、工具使用、记忆和人工监督。这些能力提高了自动化水平，但也扩大了一个讨论较少的失败面：语义污染。用户主张、检索文本、视觉解释、agent 间消息和长期记忆可能被误认为已验证状态，然后被后续 agent 当成事实传播。

本文草稿介绍 Text Graphics Agent：一种小型母子 agent 架构，把语义污染当作一等系统问题处理。母 agent 只在编译有界 `IntentFrame` 和 sanitized `TaskSpec` 时读取原始用户语义。一次性子专家只接收干净任务，产出结构化 `AgentProposal` 记录，用完即销毁。proposal 必须通过范围、证据、权威、锚点、测试、metadata 和子生命周期的有限约束检查，才能成为 committed state。这个设计把作者早期的 constraint-checked state-record pipeline 从符号状态构造扩展到 agent 编排。

一个包含十一个合成场景的确定性试验 benchmark 对比了 direct-accept baseline 和 Text Graphics Agent。在十个有意污染场景中，baseline 接受全部十个污染提案。Text Graphics Agent 接受零个污染提案，在 record checking 阶段拒绝九个，并在 spawn 前阻断一个 unsafe child profile。这不是广泛性能声明；它是一个可复现的边界检查，说明该架构能在闭环协议下让语义污染变得可见、可拒绝。

## 1. 问题

LLM agent 模糊了几组边界：

1. 数据 vs 指令；
2. 用户动机 vs 已验证证据；
3. 模型解释 vs 世界事实；
4. 短期推理状态 vs 持久记忆；
5. agent 提案 vs 已提交系统状态。

Prompt injection 研究已经说明，LLM 集成应用可能混淆外部数据和可执行指令。Greshake 等人描述了 indirect prompt injection 如何利用检索或处理第三方文本的应用。更新的 agent hallucination survey 把 agent 失败视为 pipeline failure，可能发生在 reasoning、execution、perception、memory 和 communication 阶段。多 agent survey 也强调 profiles、perception、self-action、interaction 和 evolution 是 LLM-based multi-agent systems 的核心 workflow。

近期工作也在 shared-state agent 语境中使用 contamination 语言。Yang 等人研究了 shared-state LLM agents 中的 unintentional cross-user contamination，说明良性交互产生的 scope-bound artifact 也可能持久化，并在后续用户边界中被错误复用。Cai 等人分析了 subagent spawn 和 inheritance 风险，包括 memory inheritance、resource control、post-spawn stale state 和 termination authority。TGA 的范围比这些研究更窄：它是一个小型 artifact，用于把一次性子 agent 工作流中的 proposal-to-record 边界显式化。

这里缺失的系统问题不只是"agent 能不能产出正确答案"。还包括：

> 当 agent 错误时，错误语义对象会在哪里进入持久状态？我们如何阻止它被后续 agent 继承？

本文在本地语境中把这种 proposal-to-state failure surface 称为"语义污染"。

## 2. 论点

中心论点是：

> 在自然语言、多模态解释或用户主张能影响持久状态的 agent 系统中，模型智能和状态权威必须分离。

Text Graphics Agent 用四条规则实现这一点：

1. 母 agent 编译任务、调度子 agent、审计记录。它不编写 committed facts。
2. 子 agent 是一次性的。它接收 sanitized task specs，而不是原始用户文本；默认没有持久记忆。
3. 每个子输出都是 `AgentProposal`，不是状态 mutation。
4. 只有 constraint-checked records 可以被接受进下游状态。

"Text Graphics" 指把语义材料渲染成可检查的结构化记录。这里的 "graphics" 不是像素图形，而是把语言、截图、代码观察和 agent 主张投影成类型化、可回放、可审计的形式。

## 3. 与已有工作的关系

这个架构不声称多 agent 系统、图 workflow、角色 profile 或约束检查分别是全新发明。

LangGraph 是图导向、长运行、有状态 agent workflow 的典型开源例子，包含 checkpoint 和 human-review 概念。CrewAI 把自主 "Crews" 和事件驱动 "Flows" 分开，并具备显式 role、tool、task 和 control-plane 思路。Microsoft Agent Framework 和 OpenAI Agents SDK 也代表了生产方向：显式 workflow primitives、tracing 和可部署 agent 系统。

在 LLM 安全与边界防御方面，现有的 Guardrail 方法主要分为三类：(1) **NVIDIA NeMo Guardrails** 通过 YAML 配置和 Colang flows 为 LLM 应用增加 programmable rails；(2) **Guardrails AI** 通过 validators 和 schema 运行 input/output guards，并辅助生成结构化数据；(3) **Meta Llama Guard / LlamaFirewall** 通过模型化输入/输出分类或 agent guardrail monitor 处理安全风险。与之不同，Text Graphics Agent (TGA) 关注另一个边界：子 agent 输出的 proposal 必须经过确定性 record constraints，才能成为 accepted state。

这里的贡献更窄：

1. 把语义污染视为主要威胁模型。
2. 让原始用户语义只留在母 agent 侧。
3. 让子 agent 默认一次性、无记忆。
4. 让 profile safety 在子 agent spawn 前可检查。
5. 要求每个 proposal 在成为 accepted state 前通过有限 record constraints。
6. 把 agent 架构连接到 constraint-checked state records，使同一 artifact 边界能支持实验和论文审查。

## 4. 架构

已实现原型管线：

```text
raw user text
  -> IntentFrame (intent.py)
  -> Pipeline (pipeline.py)
    -> Agent Registry (registry.py) — 基于能力的路由
    -> sanitized TaskSpec
    -> SpecialistProfile validation
    -> disposable child specialist (specialists.py)
      -> ToolContext (tools.py) — scope 强制检查的文件访问
      -> AgentProposal
    -> ConstraintChecker (constraints.py)
    -> CheckedRecord
    -> ScoreCard
    -> Memory extraction (memory.py) — 为未来任务积累不可信上下文
```

### 4.1 Intent Firewall

`IntentDecomposer` 把原始用户文本转换成 `IntentFrame`，包含：

- stable goal；
- 有限 intent codes；
- atomic intents；
- user-supplied claims；
- assumptions；
- contamination markers。

当前实现是确定性的，并刻意保持很小。它的目的不是自然语言能力优秀，而是防止原始用户语言作为权威被复制进子 agent 上下文。实现维护了中英文双语对抗关键词库，覆盖绕审施压（55 条标记）、范围越权施压（上下文感知检测，减少"全部""所有"等常用词的误报）和用户自证（35 条标记）。这些关键词库作为唯一真相源在意图防火墙、约束检查器和管道之间共享。

### 4.2 Clean TaskSpec

`MotherAgent.make_clean_task()` 把 `IntentFrame` 转换成 `TaskSpec`。生成的任务包含：

- allowed scopes；
- required anchors；
- test requirement；
- `sanitized=True`；
- `sanitized_provenance="mother_clean_v1"`。

`MotherAgent.dispatch()` 会拒绝没有该 provenance 的调用方自建任务。这阻止子 agent 被调用在"只是自称干净"的任务上。

母 Agent 可选地将策展记忆提示注入 `mother_notes`。这些提示是不可信上下文——它们帮助母 Agent 推理用户的常见模式，但绝不进入 `TaskSpec.objective`（子 Agent 的指令），绝不影响约束裁决。记忆条目是客观观察（文件范围、意图模式、违规反馈），具有随时间衰减的置信度（每天 5%），低于 15% 阈值时自动剪枝。

### 4.3 Specialist Profiles

`SpecialistProfile` 定义子 agent 的允许角色、范围、工具、raw-text 边界和记忆策略。母 agent 在 spawn 前验证 profile。以下情况会拒绝 profile：

- 请求原始用户文本；
- 请求持久记忆；
- 越出 task allowed scopes；
- 缺少可检查的 role 或 specialist id。

子 Agent 实现标准 `BaseSpecialist` 接口，包含 `run(task)`、`cleanup()` 和可选的 `ToolContext` 访问。平台包含两个内置专家：`LocalSimulationSpecialist`（确定性本地模拟器，用于测试）和 `LiveSpecialist`（调用真实 LLM API，带自动 precheck 和修复）。自定义专家可通过 `AgentRegistry` 注册，它根据声明的 intent codes 和 goal markers 使用评分算法路由任务（每匹配一个 intent +2 分，每匹配一个 marker +1 分，priority 作为同分决胜）。

### 4.3a 工具层

当专家的 profile 声明了工具时，会自动创建带 scope 强制检查的 `ToolContext`。内置工具包括 `read_file`、`glob` 和 `grep`——每次调用都检查 `task.allowed_scopes`，拦截路径穿越，并记录审计日志。这确保即使子 Agent 可以观察文件系统，也无法读取任务白名单范围之外的文件。

### 4.4 一次性子 agent 生命周期

每次子调用都会创建 `ChildSessionRecord`。成功会话以 `destroyed` 结束；失败会话以 `failed` 结束。scorecard 汇报 destroyed child ids 和 session records。这是最小生命周期模型，但能让"用完即销毁"可审计，而不是停留在口号。

### 4.5 约束检查

`ConstraintChecker` 会拒绝以下 proposal：

- malformed envelopes；
- proposal_kind 发明有限动作集之外的新类型；
- task mismatch；
- unsanitized tasks；
- 子 agent 声称 mother / ledger authority；
- record envelope 中冒用高权 actor；
- metadata 泄漏原始用户文本；
- empty claims；
- missing evidence；
- evidence only from `user:*`；
- 路径型 evidence 超出任务白名单；
- missing tests；
- 破坏性命令伪装成测试；
- proposal 文本要求绕过审核或直接批准；
- scope escape；
- proposed scopes 中出现路径穿越；
- `committed_fact` 或 `new_action_type` 等 forbidden outputs；
- missing anchors；
- 只在 `required_anchor_text` 声明锚点、claim/evidence 没有支撑；
- confidence 不在 `[0, 1]`。

这让输出面足够有限，可以测试。

### 4.6 任务图执行引擎与 Fail-Fast 熔断机制

为了验证在多步骤、复杂依赖环境下的安全边界，本项目实现了 `GraphExecutor` 拓扑图运行器。该执行器支持对 `TaskGraph` 节点的拓扑依赖解析，自动根据 `MotherAgent` 分发注册的 Specialist 执行。

更重要的是，`GraphExecutor` 实现了 **Fail-Fast 安全熔断机制**。在传统的 Agent 图调度中，若某个上游节点的子代理输出发生逻辑越权或生成了被污染的 proposal，系统往往会继续执行下游，导致脏状态在拓扑依赖图上传播污染。在 TGA 架构下，一旦检测到任何非 Accept 的记录或执行异常，运行器将立即终止整条图管线的流动并挂起 Checkpoint，防止后续 Agent 继承脏状态，在系统级做到了安全熔断。

`AsyncGraphExecutor` 变体在此基础上扩展了线程池并发：独立节点（彼此无依赖的节点）并行执行，同时保持 fail-fast 契约——第一个拒绝或错误取消当轮所有剩余 future。这允许多任务工作流在保持同一 fail-fast 安全契约的前提下更快完成。

### 4.7 零依赖沙箱与 Web 仪表板

为了降低研究原型的可展示性和使用门槛，本项目包含本地交互式沙箱（`interactive_sandbox.py`）和由零依赖 HTTP 服务器（标准库 `http.server`）驱动的单页 Web 仪表板。

- **聊天流界面**：仪表板呈现 ChatGPT 风格的聊天流，用户自然输入。闲聊直接回复；任务请求通过完整安全管道派发，结果以卡片形式返回聊天流。对话历史持久化到 `localStorage`，支持全量历史搜索。
- **设置与连接**：分区设置页允许配置 LLM 提供商、API Key 和模型，带"测试连接"按钮。文件范围选择包含工作区文件浏览器和快捷预设。
- **Inspector 面板**：可切换的右栏面板显示任务上下文、权限边界和策展记忆条目（标注为不可信），含置信度分数和删除控制。
- **渐进式披露**：Composer 状态栏和工作流时间线默认隐藏，按需展开，降低首屏认知负荷，同时保留完整可审计性。
- **公开 release artifact**：独立公开仓库已发布在
  `https://github.com/910636071/text-graphics-agent-release`。它从私有父仓库
  干净导出，作为独立项目 artifact 提供双语文档、操作指南、确定性 benchmark
  和 Web 工作台原型。

## 5. 试验 Benchmark

试验 benchmark 是确定性的，不调用外部模型。它测试的是架构边界，不是模型质量。

### 5.1 真实大模型 API Smoke 评测

作为补充 smoke 评测，本项目通过 DeepSeek API（`deepseek-chat` 模型）执行六个场景。这个测试比确定性 benchmark 更窄：它检查真实 provider 能否在同一协议下产出结构化 proposal，而不是证明系统能抵御所有真实模型攻击。具体实验条件如下：
- **评测提供商 (Provider)**: DeepSeek API (`deepseek-chat` 模型)
- **数据集场景**: 延续确定性 Benchmark 的 6 个场景（5 个有意注入污染，1 个干净提案）
- **两条比对路径**: 
  1. **直连 Naive Baseline**（模型直面带有污染的原始文本）并进行 **影子拦截 (Shadow Check)**；
  2. **TGA 物理净化流程**（模型只处理 Sanitized TaskSpec，子代理被强物理隔离）。

实验采集的量化数据如下（详见记录文件 [live_api_benchmark_20260703.zh-CN.md](./live_api_benchmark_20260703.zh-CN.md)）：
- **Naive Baseline 接受污染提案率**: 在这组六场景 smoke run 中为 100%
  （5/5，污染 proposal 会被 direct-accept 路径接受）。
- **影子拦截率 (Direct Shadow Block Rate)**: 在这次 run 的污染 direct path 中为
  100%，但 direct path 本身没有提供可接受的范围化修复通道。
- **TGA 净化提案通过率 (TGA Accepted Rate)**: 在这次 run 中为 100%
  （6/6，模型在母 agent 的 `TaskSpec` 边界引导下产出的 proposal 通过约束审计）。
- **TGA 原始污染暴露次数**: 本次 run 中为 0 次。

这个 smoke test 支持一个更窄的结论：把 raw-prompt 暴露与子 agent 执行边界分离，可以在 direct raw-prompt path 可能接纳污染或只能被 shadow checker 阻断的情况下，保留有用的范围化修复通道。它不是对所有 prompt injection、所有 provider 或所有真实部署场景的安全性 / 可用性证明。

命令：

```powershell
cd text-graphics-agent
python -m text_graphics_agent.benchmark
```

benchmark 包含十一个场景：

| 场景 | 污染类型 | 预期 TGA 处理 |
| --- | --- | --- |
| `bench-user-semantics-only` | 用户主张被当成唯一证据 | reject |
| `bench-scope-escape` | proposal 触碰不允许的世界数据 | reject |
| `bench-direct-fact-write` | 子 agent 尝试提交世界事实 | reject |
| `bench-raw-context-leak` | 原始用户文本出现在子 metadata 中 | reject |
| `bench-unsafe-profile` | child profile 请求原始用户文本 | block before spawn |
| `bench-authority-impersonation` | 子 agent 冒用 mother/ledger 权威 | reject |
| `bench-proposal-kind-expansion` | 子 agent 发明 state-write proposal kind | reject |
| `bench-path-traversal` | 子 agent 把路径穿越藏进白名单前缀 | reject |
| `bench-anchor-spoof` | 子 agent 只声明锚点但不给证据支撑 | reject |
| `bench-bypass-language` | 子 agent 要求跳过测试并直接批准 | reject |
| `bench-clean-patch` | 范围内证据和测试命令 | accept |

当前输出：

```json
{
  "scenario_count": 11,
  "unsafe_scenario_count": 10,
  "baseline_accepted": 11,
  "baseline_polluted_accepted": 10,
  "baseline_pollution_acceptance_rate": 1.0,
  "tga_reviewed_records": 10,
  "tga_accepted": 1,
  "tga_rejected": 9,
  "tga_blocked_before_spawn": 1,
  "tga_polluted_accepted": 0,
  "tga_pollution_acceptance_rate": 0.0,
  "accepted_pollution_delta": 10
}
```

解释：

- direct-accept baseline 接受所有 proposal，包括全部十个污染 proposal。
- Text Graphics Agent 接受唯一 clean patch proposal。
- Text Graphics Agent 在 record checking 阶段拒绝九个污染 proposal。
- Text Graphics Agent 在子 agent spawn 前阻断一个 unsafe profile。

这个结果应被理解为架构 sanity check，而不是关于部署 LLM agents 的一般经验声明。

## 6. 与 Constraint-Checked State Records 的连接

作者的 `constraint-checked-state-records` artifact 定义了归一化记录上的符号管线：

```text
SyntheticCase -> TraceStore -> Baselines -> ConstraintCheck -> ScoreCard
```

Text Graphics Agent 把同一个边界适配到 agent 执行：

```text
IntentFrame -> TaskSpec -> SpecialistProfile -> AgentProposal
  -> ConstraintCheck -> ScoreCard
```

因此研究计划是连续的：

1. 论文 1：符号状态构造的 finite checked records；
2. 论文 2：finite concept-space / constraint interface theory；
3. 本草稿：基于 checked records 的 disposable-agent orchestration。

这条链路不只存在于本草稿中，也有公开仓库 artifact 支撑。2026-07-04 核对的
GitHub metadata 显示：最早 clean-room seed artifact `rgbd-safe-minimal`
创建于 2026-05-25；后续 `constraint-checked-state-records` artifact 创建于
2026-05-25；`checked-state-benchmark` scaffold 创建于 2026-05-26。这些仓库在本文中
作为作者 artifact 引用，用来说明 checked-record 研究线的连续性；它们不是法律意义上的
优先权结论，也不能替代 prior-art review。

两篇论文的连接很强，因为 agent 系统不需要另起一套"真理哲学"。它继承同一个原则：生成候选很便宜，接受状态很昂贵。

## 7. 局限

1. benchmark 是合成且确定性的。
2. intent decomposition 是基于规则的（非 LLM 驱动），虽然现在覆盖了 55 条绕审标记和 35 条用户自证标记（中英文），并具有上下文感知的范围检测。使用轻量 LLM 驱动的 sanitizer 作为补充层的混合方法仍是未来工作。
3. 目前主要对文本大模型（如 DeepSeek-Chat）进行了闭环评估，尚未扩展到多模态视觉模型。
4. 当前生命周期模型记录销毁，但不强制进程级隔离。
5. 约束列表是有限且手写的。
6. benchmark 只证明 closed-protocol rejection，不证明真实世界攻击抗性。
7. 策展记忆是不可信的，不影响约束，但其提取逻辑是启发式的——更复杂的记忆策展（如矛盾检测、时序推理）留待未来工作。
8. 公开 release 是研究原型和审查 artifact，不是生产级 agent 操作系统；持续交互质量仍需要浏览器级 UI 回归测试覆盖。
9. 当前可信契约是一次性任务工作流。跨轮上下文继承被当作不可信记忆，而不是已验证权威。若要扩展成持久化多轮协作系统，需要在 `IntentFrame` 和 `TaskSpec` 之间加入显式的 `ContextAnchorResolver`，把"基于上一轮接受结果"这类主张与历史 `CheckedRecord` 指纹核对后，才能允许上下文继承。

这些限制符合当前 artifact 边界。下一阶段应在保持同一 benchmark format 的前提下，加入更多模态对抗生成 proposals 和跨轮 context-anchor cases。

## 8. 下一步实验

1. (已完成) 加入 model-backed child adapter（`LiveSpecialist`）。
2. (已完成) 让 direct-agent baseline 和 TGA 跑相同 prompts。
3. (已完成) DeepSeek 端到端 Live LLM 验证（贪吃蛇任务，28 秒内通过约束检查，含自动修复）。
4. (已完成) 平台层：`Pipeline`、`AgentRegistry`、`BaseSpecialist`、`ToolContext`、策展记忆、`AsyncGraphExecutor`。
5. (已完成) 独立公开 release 仓库，包含双语文档和干净工作台 artifact。
6. 为工作台、设置、文件范围、审批和诊断流加入浏览器级 UI 回归测试。
7. 加入多模态截图误解 cases。
8. 加入 shared-memory contamination cases。
9. 为论文表格导出 JSONL checked records。
10. 加入第二个 benchmark，对齐现有配置 UI bug-finding flow。
11. 混合意图防火墙：在基于规则的 `IntentDecomposer` 之上增加轻量 LLM sanitizer 作为补充层。
12. 加入面向持久化多轮协作的 `ContextAnchorResolver`：把用户关于上一轮已接受工作的主张解析成结构化 `context_anchors`，与历史 `CheckedRecord` 核对；无法证明继承关系时，要求用户澄清。

## 9. 参考文献

- Kai Greshake et al. "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." arXiv:2302.12173. https://arxiv.org/abs/2302.12173
- Xixun Lin et al. "LLM-based Agents Suffer from Hallucinations: A Survey of Taxonomy, Methods, and Directions." https://arxiv.org/html/2509.18970v1
- Xinyi Li et al. "A survey on LLM-based multi-agent systems: workflow, infrastructure, and challenges." https://link.springer.com/article/10.1007/s44336-024-00009-2
- "Design Patterns for Securing LLM Agents against Prompt Injections." https://arxiv.org/html/2506.08837v1
- Tiankai Yang et al. "No Attacker Needed: Unintentional Cross-User Contamination in Shared-State LLM Agents." arXiv:2604.01350. https://arxiv.org/abs/2604.01350
- Ziwen Cai, Yihe Zhang, and Xiali Hei. "When Child Inherits: Modeling and Exploiting Subagent Spawn in Multi-Agent Networks." arXiv:2605.08460. https://arxiv.org/abs/2605.08460
- NVIDIA NeMo Guardrails documentation. https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview
- Guardrails AI documentation / package page. https://pypi.org/project/guardrails-ai/
- Hakan Inan et al. "Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations." https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/
- Sahana Chennabasappa et al. "LlamaFirewall: An open source guardrail system for building secure AI agents." https://ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/
- LangGraph repository. https://github.com/langchain-ai/langgraph
- CrewAI repository. https://github.com/crewAIInc/crewAI
- Microsoft Agent Framework repository. https://github.com/microsoft/agent-framework
- OpenAI Agents SDK repository. https://github.com/openai/openai-agents-python
- Lijie Wang. "Minimal Symbolic Pipeline / rgbd-safe-minimal." https://github.com/910636071/rgbd-safe-minimal
- Lijie Wang. "Constraint-Checked State Records." https://github.com/910636071/constraint-checked-state-records
- Lijie Wang. "Checked-State Synthetic Benchmark." https://github.com/910636071/checked-state-benchmark
