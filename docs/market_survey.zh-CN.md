# Agent 仓库调研

英文原文：[Agent Repository Survey](./market_survey.md)。

调研日期：2026-07-03。

这份笔记记录原型从当前开源 agent 框架中吸收了什么，以及本项目有意拒绝什么。

## 来源

- LangGraph: https://github.com/langchain-ai/langgraph
- CrewAI: https://github.com/crewAIInc/crewAI
- Microsoft Agent Framework: https://github.com/microsoft/agent-framework
- AutoGen legacy repository: https://github.com/microsoft/autogen
- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
- NVIDIA NeMo Guardrails: https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview
- Guardrails AI: https://pypi.org/project/guardrails-ai/
- Meta Llama Guard: https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/
- Meta LlamaFirewall: https://ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/

## 吸收

1. **状态图，而不是聊天循环。**
   LangGraph 对这里有用的点是显式状态和节点推进。原型加入 `TaskGraph`、`TaskNode` 和 `ExecutionCheckpoint`，避免把运行中的 transcript 当状态。

2. **角色和任务是配置，不是散文。**
   CrewAI 的实践价值在于显式 role / task / tool 声明。原型加入 `SpecialistProfile`，让子 agent 的角色、工具访问、范围、记忆策略和 raw-text 边界在 spawn 前可检查。

3. **workflow 是生产对象。**
   Microsoft Agent Framework 和 OpenAI Agents SDK 都指向可测试的小型 workflow primitives。原型刻意保持 primitives 很小：intent frame、clean task、specialist profile、graph node、proposal、checked record、scorecard。

4. **人工审查应该在 checkpoint 上。**
   项目本身已有 checked-record 纪律。原型把它映射到 task graph checkpoints 和 scorecards，而不是让母模型直接提交 accepted output。

## 拒绝

1. **子 agent 持久记忆。**
   本项目把语义污染视为主要风险。请求 persistent memory 的 child profile 会在 dispatch 前被拒绝。

2. **子上下文中的原始用户文本。**
   母 agent 可以读取原始用户语言并编译 intent codes。子 agent 只拿 sanitized tasks。允许 raw user text 的 profile 会被拒绝。

3. **把角色扮演社会当成权威。**
    角色多样性有利于对抗性审查，但 roleplay 不能写事实。每个子输出仍必须成为 `AgentProposal`，再由有限约束检查。

4. **框架锁定。**
   这个文件夹保持仅依赖标准库。目标是在选择外部运行时前，先把契约做成可迁移的。

## 前沿安全防御框架调研对比

为了明确本项目（Text Graphics Agent, TGA）在 LLM 安全领域的学术和技术定位，我们对当前业界的 LLM 安全与 Guardrail 框架进行了深入调研：

1. **NVIDIA NeMo Guardrails**
   - **核心原理**：使用 YAML 配置和 **Colang** flows 定义 programmable rails。Rails 可以在 LLM 的输入、输出、对话流和工具路径上增加控制逻辑。
   - **主要用途**：防止对话跑题、控制多轮对话的行为逻辑、限制特定工具的调用路径。
   - **TGA 的不同之处**：NeMo Guardrails 为 LLM 应用提供 programmable rails，但默认并不施加 TGA 这种 child-proposal-to-checked-record 权威模型。TGA 贯彻 **“智能与权力解耦（Authority Separation）”**——子代理仅能“提案（Propose）”，最终的账本状态接受交由确定性的 `Constraint` 链条裁决。

2. **Guardrails AI**
   - **核心原理**：通过 input/output guards、validators，以及 schema / Pydantic 约束进行结构化数据生成和验证。
   - **主要用途**：保证输出的数据格式（如强制 JSON 格式化）和内容的合规度。
   - **TGA 的不同之处**：Guardrails AI 主要验证模型输入/输出和结构化数据。TGA 工作在编排边界：子 agent 的上下文被收窄到 sanitized `TaskSpec`，子 agent 只能提交 proposal，再进入确定性 record checking。

3. **Meta Llama Guard / LlamaFirewall**
   - **核心原理**：Llama Guard 用于 prompt/response 的模型化内容审核；LlamaFirewall 面向 prompt injection、agent misalignment 和 insecure code 等 agent 风险提供 guardrail monitor。
   - **主要用途**：内容安全和 agent security monitoring。
   - **TGA 的不同之处**：Meta 工具增加的是模型化或 monitor-based 的安全层。TGA 是零依赖的确定性 record gate，专门用于一次性子 agent 编排中的状态入账保护。

| 维度 | TGA (本项目) | NVIDIA NeMo Guardrails | Guardrails AI | Meta Llama Guard / LlamaFirewall |
| :--- | :--- | :--- | :--- | :--- |
| **主要定位** | 一次性子代理流的**状态隔离防火墙** | LLM 应用的 **programmable rails** | **输入/输出验证** 与结构化生成 | **内容安全 / agent security monitoring** |
| **核心机制** | 意图解耦 (Intent Firewall) + 模块化 Constraint 账本拦截 | YAML + Colang flows + guardrail APIs | Validators + schema/Pydantic + Guardrails Hub | 安全分类器 / agent guardrail monitor |
| **子任务原始输入屏蔽** | **支持** (子 agent 只接收 sanitized TaskSpec) | 不是默认抽象 | 不是默认抽象 | 不是默认抽象 |
| **权力分离 (Authority)** | **支持** (Children Propose, Records Decide) | 不是核心契约 | 不是核心契约 | 不是核心契约 |
| **拓扑图链式熔断** | **支持** (基于 GraphExecutor top-ready 熔断) | 取决于框架集成 | 取决于框架集成 | 取决于 monitor 配置 |
| **运行时开销** | **极轻量** (纯 Python 标准库规则检查) | 取决于 rails 和 runtime | 取决于 validators 和 re-ask 策略 | 取决于 scanner / model 配置 |

## 已实现的平台特性：图执行引擎 (`GraphExecutor`)

根据上述调研和适配目标，我们已实现 `GraphExecutor` 运行器（位于 `graph.py`）：
1. 加载并遍历 `TaskGraph`；
2. 动态拓扑查找 `ready_nodes()`；
3. 严格匹配已注册且 profile 有效的 specialists，通过 `MotherAgent` 进行 dispatch；
4. 捕获并记录每个节点的 `ExecutionCheckpoint` 行（状态包括 completed / failed 以及接受与拒绝指标）；
5. 遇到任何 rejected record 或 specialist 抛出异常立即 Fail-Fast 停止执行。

## 下一步适配

1. 支持进程级别隔离的子 Agent 执行沙箱（例如结合 `subprocess` 或本地容器），防止子代理越权读取内存或文件。
2. 接入多 Provider（例如 DeepSeek + Gemini + OpenAI）混合调度以及开发更强大的对抗污染生成评估集。
3. 将 TaskGraph 引擎同桌面宠物的底层事件链系统（event log）进行更深度的本地测试集成。
