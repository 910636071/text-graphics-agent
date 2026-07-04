# Text Graphics Agent 公开包装

英文原文：[Text Graphics Agent Packaging](./packaging.md)。

这份文件用于 GitHub、Figma、论文摘要和短技术演示。措辞必须克制：这不是 AGI 声明，也不是通用多 agent 平台。

## 一句话定位

Text Graphics Agent 是安全优先的 Agent 平台——模型负责提案，检查后的记录负责裁决——面向一次性子 Agent 工作流的语义防火墙。

## 短介绍

现代 Agent 系统会把用户主张、检索文本、截图、模型解释和记忆混在同一个上下文里。一旦错误语义进入持久状态，后续 Agent 会把它们当事实继承。

Text Graphics Agent 把智能和权力分开。母 Agent 只在编译 clean task 时短暂读取原始用户语言。一次性子 Agent 只接收 sanitized task specs，产出结构化 proposals，用完即销毁。proposal 只有通过范围、证据、权威、锚点、测试、metadata 和生命周期等有限检查后，才能进入状态。

平台包含标准 `BaseSpecialist` 接口、基于能力的 Agent 路由、scope 强制检查的工具访问、策展记忆（不可信——绝不影响约束）、以及带对话持久化的聊天流界面。

## 标语

- Models propose. Records decide.
- 不要让最聪明的模型直接成为状态写入者。
- 用户语义是动机，不是证据。
- 生成候选很便宜，接受状态很昂贵。
- 面向需要记忆但不能被污染的 agent 系统的状态防火墙。

## README 头图文案

```md
# Text Graphics Agent

**面向一次性子 agent 工作流的语义防火墙。**

Text Graphics Agent 把语义污染当作系统问题处理。原始用户请求先由母 agent 编译成 sanitized tasks。子 agent 只接收 clean task specs，产出结构化 proposals，用完即销毁。只有 constraint-checked records 能进入下游状态。

当前 artifact：

- 标准库 Python 原型；
- intent firewall；
- specialist profiles；
- task graph primitives；
- checked proposal records；
- deterministic contamination benchmark；
- paper draft。
```

## Figma Pitch 结构

工作设计稿：https://www.figma.com/design/DqvS5sjyVDNQ9c5vkRcruY

Figma 文件是权限控制的工作资产。公开发布时，除非 Figma 文件本身公开，否则应导出 social preview image 并链接到公开资产。

Frame：

1. `01 / Cover - Positioning`
   - 主信息：Models propose. Records decide.
   - 视觉：raw semantics -> mother agent -> checked records。

2. `02 / Architecture and Benchmark`
   - 管线：Raw user text -> IntentFrame -> Clean TaskSpec -> Profile check -> Disposable child -> Proposal -> Checked Record。
   - 证据：11 个场景，10 个 unsafe；baseline 接受 10 个污染提案；TGA 接受 0 个污染提案；1 个 unsafe profile 在 spawn 前被阻断。

3. `03 / Artifact and Roadmap`
   - 代码 artifact、论文草稿、研究链接。
   - 下一步实验：model-backed adapters、真实 prompts、多模态 screenshot cases、论文表格用 JSONL records。

## Benchmark 声明

安全措辞：

> 在一个包含十个有意污染场景的确定性试验 benchmark 中，direct-accept baseline 接受全部十个污染提案。Text Graphics Agent 接受零个污染提案，在 record checking 阶段拒绝九个，并在 spawn 前阻断一个 unsafe child profile。

避免措辞：

- “解决幻觉”；
- “防止所有 prompt injection”；
- “这是 AGI 架构”；
- “保证安全”；
- “打败 LangGraph / CrewAI / OpenAI Agents SDK”。

## 对比定位

Text Graphics Agent 不应被包装成 LangGraph、CrewAI、Microsoft Agent Framework 或 OpenAI Agents SDK 的替代品。它是一个协议层，可以放在这些运行时之上或内部：

- LangGraph 提供有状态执行和图控制。
- CrewAI 提供角色 / 任务 / 团队建模。
- OpenAI Agents SDK 提供生产 agent primitives 和 tracing。
- Text Graphics Agent 提供语义污染边界和 checked state entry。

## 论文摘要压缩版

本文介绍 Text Graphics Agent：一种母子 agent 架构，将语义污染视为一等系统风险。原始用户语言由母 agent 编译成 sanitized task specs；一次性子 agent 执行 clean tasks 并输出结构化 proposals；只有 constraint-checked records 能进入持久状态。确定性试验 benchmark 显示，在十个污染场景下，direct-accept baseline 接受全部污染提案，而 Text Graphics Agent 不接受任何污染提案，并在 spawn 前阻断一个 unsafe child profile。

## 命名

使用：

- Text Graphics Agent
- TGA
- semantic firewall
- disposable child-agent workflow
- checked-record pipeline

避免：

- AI town agent；
- AGI mother brain；
- world model platform；
- anti-Gemini / anti-Claude framing。
