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
   - **核心原理**：使用专门的行为编程语言 **Colang** 定义状态机。Rails 可以在 LLM 的输入、输出和对话流之间强行设定流转限制。
   - **主要用途**：防止对话跑题、控制多轮对话的行为逻辑、限制特定工具的调用路径。
   - **TGA 的不同之处**：NeMo Guardrails 专注于“对话流管理和规则路由”，但 LLM 仍作为权威状态的直接生成器。而 TGA 贯彻了 **“智能与权力解耦（Authority Separation）”** 的设计——子代理仅能“提案（Propose）”，最终的账本状态接受完全交由确定性的 `Constraint` 链条裁决。

2. **Guardrails AI**
   - **核心原理**：定义结构化 Schema（通常结合 Pydantic）并配置 Validators，对 LLM 输出内容的结构、质量（如幻觉、PII 泄露、毒性等）进行静态或动态审查，并在检测到错误时提供重试 (Re-ask) 机制。
   - **主要用途**：保证输出的数据格式（如强制 JSON 格式化）和内容的合规度。
   - **TGA 的不同之处**：Guardrails AI 关注于“内容解析与格式验证（内容级纠错）”。而 TGA 针对的是系统架构层面的“防污染”。TGA 甚至限制子代理只接受 Sanitized TaskSpec（隐藏了原始用户输入），从而阻断了由于直接用户话语带偏而诱导子代理越权提案的漏洞。

3. **Llama Guard**
   - **核心原理**：Meta 微调的专属大语言安全分类模型，对提示词与响应进行安全分类评判（Safe/Unsafe + 违规类别）。
   - **主要用途**：输入/输出的内容审核（Content Moderation）。
   - **TGA 的不同之处**：Llama Guard 依赖额外模型的推理开销（延迟高），属于基于分类模型的安全判定（无物理隔离）。TGA 是一个不依赖外部大模型的、极其轻量的本地有限状态检查防火墙，专为 Disposable Agent 编排的工作流提供隔离边界。

| 维度 | TGA (本项目) | NVIDIA NeMo Guardrails | Guardrails AI | Meta Llama Guard |
| :--- | :--- | :--- | :--- | :--- |
| **主要定位** | 一次性子代理流的**物理状态隔离防火墙** | 对话流转与工具路径的**编程状态机** | 结构化输出的**内容/格式校验器** | 输入/输出的**安全内容分类模型** |
| **核心机制** | 意图解耦 (Intent Firewall) + 模块化 Constraint 账本拦截 | Colang 编程定义对话 Rails | 带有 Validators 的 XML/Schema 校验 | Llama 专属微调分类模型 |
| **原始输入屏蔽** | **支持** (子代理物理上接收不到 raw request，仅拿 clean TaskSpec) | 不支持 (模型直接暴露在 raw prompt 下) | 不支持 (模型直接暴露在 raw prompt 下) | 不支持 (仅对 raw text 进行分类检测) |
| **权力分离 (Authority)** | **支持** (Children Propose, Records Decide) | 不支持 (模型仍是直接状态写入者) | 不支持 (模型仍是直接状态写入者) | 不支持 (仅进行 Yes/No 安全检测) |
| **拓扑图链式熔断** | **支持** (基于 GraphExecutor top-ready 熔断) | 不支持 | 不支持 | 不支持 |
| **运行时开销** | **极轻量** (纯 Python 标准库规则检查) | 中等 (需要 Colang 运行时和流转换) | 中等 (XML 解析与 validators 重试) | 较高 (依赖额外的微调大模型推理) |

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
