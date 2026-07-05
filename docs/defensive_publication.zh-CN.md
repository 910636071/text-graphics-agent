# 防御性公开：Text Graphics Agent 协议边界

公开日期：2026-07-04

作者：Lijie Wang，独立研究者

联系邮箱：wanglijie100@gmail.com

Artifact：`text-graphics-agent/`

相关文档：
- [系统架构](./architecture.zh-CN.md)
- [论文草稿](./paper_draft.zh-CN.md)
- [公开来源 artifact 记录](./provenance_artifacts_20260704.zh-CN.md)
- [引用与相似性审计](./citation_audit_20260704.zh-CN.md)

## 状态

本文是一份公开技术披露，用于让 Text Graphics Agent (TGA) 的协议边界更容易被检索、引用和举证。它按防御性公开和现有技术辅助材料写作；它不是法律意见，不是专利申请，也不主张本项目拥有“AI 安全”“agent guardrail”“human-in-the-loop”或“LLM 游戏”等宽泛类别。

本文要公开的是下面这组具体协议族：人类意图在被稳定化为有界任务记录前，不被视为任务权威；AI 输出在通过确定性记录检查前，不被视为可信状态。

## 技术领域

本公开涉及 LLM agent 编排、多 agent workflow、语义污染控制、proposal-to-record 验证、人类审批点，以及 LLM 辅助系统中的状态权威分离，适用范围包括 LLM agent 平台和 LLM 游戏。

## 问题陈述

LLM 系统经常模糊五组边界：

1. 用户意图 vs 可执行任务权威；
2. 检索文本或记忆文本 vs 已验证证据；
3. 模型解释 vs 持久事实；
4. 子 agent 输出 vs 已提交系统状态；
5. LLM 游戏中的玩家可见叙述 vs canonical game state。

一旦这些边界坍塌，模型幻觉、prompt injection 字符串、越界指令、陈旧记忆或未验证的玩家可见文本都可能进入持久状态。后续 agent 或游戏系统可能把这些状态继承为可信事实。

## 核心公开

TGA 公开了一种双向治理协议：

```text
人类侧：
原始用户输入
  -> Intent Firewall
  -> IntentFrame
  -> sanitized TaskSpec
  -> 任务权威

AI 侧：
一次性子 agent 输出
  -> AgentProposal
  -> ConstraintChecker
  -> CheckedRecord
  -> 可信状态
```

该系统把智能与权威分离：

- 母 agent 可以解释、澄清、路由、调度和审计；
- 子 agent 可以在有界任务内工作并提交提案；
- 原始用户文本和子 agent 输出都不会自动成为可信状态；
- 确定性约束决定输出是否可以成为已接受状态；
- 高风险转换可以要求明确的人类审批。

## 非限制性术语

以下名称只是示例。等价实现即使更换名称，只要保留相同的协议边界，也仍属于本文公开的结构族。

| TGA 术语 | 等价名称 |
| --- | --- |
| Intent Firewall | 意图稳定器、任务权威门、指令防火墙、语义防火墙 |
| IntentFrame | 稳定意图记录、有界意图框架、请求框架 |
| TaskSpec | 净化任务、工作规格、干净任务记录、带 scope 的任务契约 |
| Mother Agent | 调度器、审计器、编排器、监督 agent、路由 agent |
| Disposable Child Agent | 工作 agent、专家 agent、一次性 subagent、有界执行器 |
| AgentProposal | 提案记录、候选补丁、子输出记录、不可信提案 |
| ConstraintChecker | 记录验证器、确定性检查器、接收门 |
| CheckedRecord | 已接受记录、已拒绝记录、已验证状态转换 |
| ToolContext | scope 工具层、能力边界、文件范围包装器 |
| Curated Memory | 不可信记忆提示、审计记忆、顾问上下文 |

## 协议步骤

一种实现可执行以下步骤：

1. 接收原始用户输入。
2. 将输入分解为稳定目标、用户主张、污染标记、必要文件和验收锚点。
3. 当输入模糊、没有 scope、不安全或被包装成绕审指令时，拒绝、澄清或暂停请求。
4. 将稳定意图转换成 sanitized `TaskSpec`，避免原始用户文本进入子 agent。
5. 选择工具、scope、角色声明与任务匹配的子 agent profile。
6. 当 profile 请求不安全工具、持久记忆、提交事实权威或任务 scope 外访问权时，拒绝 spawn。
7. 在一次性生命周期中运行子 agent。
8. 通过带 scope 的 `ToolContext` 或等价能力层限制工具访问。
9. 要求子输出必须是 `AgentProposal`，而不是直接状态 mutation。
10. 对 proposal 的 metadata、evidence、scope、authority、tests、anchors 和 goal alignment 运行确定性约束。
11. 返回接受或拒绝的 `CheckedRecord`，并给出可见拒绝原因。
12. 只有 accepted record 和必要的人类审批可以影响下游可信状态。
13. 跨会话观察只能作为不可信策展记忆保存；记忆可以帮助未来母 agent 推理，但不得直接成为子 agent 指令或约束裁决依据。

## 18 条确定性检查

当前 TGA 原型实现了 18 条模块化检查。编号是描述性的，不构成限制；等价实现可以合并或拆分检查，只要保留相同的接收边界。

| # | 检查 | 拦截内容 |
| --- | --- | --- |
| 1 | Envelope | 记录元数据格式错误 |
| 2 | Proposal Kind | 超出允许动作集的伪造输出类型 |
| 3 | Task Mismatch | 指向错误 task ID 的 proposal |
| 4 | Sanitized Task | 绕过母 agent 净化的任务 |
| 5 | Authority | 子 agent 冒用 mother、ledger、system 或 commit authority |
| 6 | Metadata Leak | 原始用户文本通过 metadata 字段泄漏 |
| 7 | Claim | 空的或不可执行的修改主张 |
| 8 | Evidence | 缺少独立证据的 proposal |
| 9 | Evidence Scope | evidence path 越出 allowed scope 或包含路径穿越 |
| 10 | Test | 需要测试但缺少测试命令 |
| 11 | Test Command Safety | 破坏性或不安全 shell 命令 |
| 12 | Bypass Language | “skip tests”“approve directly”“no review”等等价绕审文本 |
| 13 | Scope | proposed file changes 越出 scope 白名单 |
| 14 | Forbidden Output | 直接写入 `confirmed_fact` 或 `committed_fact` 等持久事实 |
| 15 | Anchor | 缺失或伪造 evidence-chain anchors |
| 16 | Goal Alignment | proposal 偏离 sanitized objective |
| 17 | Confidence | confidence score 超出允许范围 |
| 18 | Patch Hunk | 越界、过大、模糊或格式错误的局部补丁 hunk |

## LLM 游戏状态边界

同一套权威分离也适用于 LLM 游戏。

在 LLM 游戏中，模型可以叙述已批准事实、润色对白、总结状态或提出面向玩家的文本。模型不应直接编写 canonical game state。Canonical game state 应由确定性规则、已验证记录、明确的人类批准转换或等价的状态权威机制产生。

一种面向游戏的映射如下：

```text
玩家输入
  -> 意图/动作稳定器
  -> 有界游戏动作
  -> 规则引擎或已验证状态转换
  -> canonical game state
  -> 已批准事实
  -> LLM 叙述/对白
  -> 玩家可见文本
```

本文不主张拥有 LLM 游戏、AI NPC、游戏对白生成或玩家可见模型叙述这些宽泛概念。本文公开的边界更窄：模型输出应被视为表达或提案，而不是 canonical game-state authority；除非它通过明确的验证或审批机制。

## 非限制性变体

本文公开的协议包括但不限于以下实现：

- `TaskSpec`、`AgentProposal`、`CheckedRecord` 被改名，但保留相同权威转换；
- 母 agent 是确定性、LLM 辅助、规则辅助或混合实现；
- 子 agent 是本地确定性 worker、真实 LLM 调用、工具执行专家或多模态解释器；
- 多个子 agent 顺序执行、并行执行或通过图执行器执行；
- 约束以函数、policy object、schema、类型检查、形式化验证器、规则引擎或数据库约束实现；
- 人类审批只用于高风险动作，或用于每个 accepted state transition；
- evidence 可以是文本、代码、文件路径、截图、OCR、结构化日志或多模态 artifact，前提是 provenance 和 scope 可检查；
- memory 被禁用、仅作顾问上下文、带衰减、人工策展，或由 context-anchor resolver 替代；
- 同一边界用于软件 agent、文档 agent、代码审查 agent、本地自动化工具、游戏 agent 或 LLM 游戏。

## 非主张与边界

本文不主张：

- 垄断 AI 安全、LLM guardrail、agent 编排、图 workflow、human-in-the-loop review 或 LLM 游戏；
- 证明系统具有通用 prompt-injection 抵抗能力；
- 证明所有幻觉都被防止；
- 提供生产安全保证；
- 独占 schema validation、tool scoping、role profile、approval prompt 等单独想法。

本文公开的贡献是一个具体组合：状态权威分离、净化任务权威、一次性子 agent 提案、确定性记录检查、可见拒绝原因，以及只有通过验证后才能进入可信状态。

## 防御性公开用途

本文旨在帮助未来读者、评审者、专利审查员或维护者识别：TGA 协议族已经在上述公开日期通过仓库历史、release artifact 和公开托管时间戳进入公共可检索材料。

若用于法律目的，请咨询合格专利律师。项目维护者也可以把本文进一步发布到带时间戳的公开渠道，例如 GitHub release、Zenodo DOI、arXiv 或其他公开仓库索引。
