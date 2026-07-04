# 引用与相似性审计，2026-07-04

英文原文：[Citation and Similarity Audit](./citation_audit_20260704.md)。

这份记录用于公开 release artifact 的全网引用与相似性排查。它不是法律结论，只是给外部审查准备的实用审计记录。

## 搜索范围

本轮排查搜索了项目的特征短语和相邻概念，包括：

- "Text Graphics Agent" 和 "semantic firewall"
- "semantic contamination" 与 LLM agents
- "disposable child agent"、"mother agent"、"child agent" 和 "TaskSpec"
- "candidate generation is cheap; accepted state is expensive"
- "Models Propose, Records Decide"
- Guardrail 框架引用：NVIDIA NeMo Guardrails、Guardrails AI、Meta Llama Guard 和 LlamaFirewall

## 发现

未发现项目特征口号或句子（如 "Models Propose, Records Decide"、"candidate generation is cheap; accepted state is expensive"）在公开网页上有直接匹配。

排查发现了若干必须补引用的相邻工作，因为它们与论文的术语或威胁模型重叠：

- shared-state LLM agent contamination："No Attacker Needed: Unintentional
  Cross-User Contamination in Shared-State LLM Agents"
- subagent spawn 与 inheritance risk："When Child Inherits: Modeling and
  Exploiting Subagent Spawn in Multi-Agent Networks"
- Guardrail 和 agent-safety 系统：NVIDIA NeMo Guardrails、Guardrails AI、Meta Llama Guard、Meta LlamaFirewall

本轮也核对了作者自己的公开仓库链条。`rgbd-safe-minimal`、`constraint-checked-state-records`
和 `checked-state-benchmark` 适合作为 checked-record 研究方向的 provenance artifacts，
但应作为作者 artifact 引用，而不是当成独立的全局优先权结论。

## 已做修改

- 在 `docs/paper_draft.md` 和 `docs/paper_draft.zh-CN.md` 中补充 shared-state contamination 与 subagent inheritance 论文。
- 将论文中的 "semantic contamination" 改写为 TGA 在本地语境中对 proposal-to-state failure surface 的命名，而不是声称创造一个全局新术语。
- 在论文参考文献中补充 Guardrails / Llama Guard / LlamaFirewall 官方来源。
- 调整 `docs/market_survey.md` 和 `docs/market_survey.zh-CN.md`，避免对其他 guardrail 系统作过强或不精确的否定。
- 新增 `docs/provenance_artifacts_20260704.md` 及中文镜像，用来记录带时间戳的公开仓库研究链条。

## 剩余风险

公开网页搜索不能证明不存在抄袭或先行工作。正式投稿前，应对最终 PDF 运行专业 plagiarism / similarity checker，并重新检查 `cs.AI`、`cs.CL` 和 `cs.CR` 的近期 arXiv 工作。
