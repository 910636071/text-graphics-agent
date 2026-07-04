# Citation and Similarity Audit, 2026-07-04

Chinese mirror: [引用与相似性审计](./citation_audit_20260704.zh-CN.md).

This note records a public-web citation and similarity check for the release
artifact. It is not a legal determination; it is a practical audit trail for
external review.

## Search Scope

The audit searched distinctive project phrases and nearby concepts, including:

- "Text Graphics Agent" and "semantic firewall"
- "semantic contamination" with LLM agents
- "disposable child agent", "mother agent", "child agent", and "TaskSpec"
- "candidate generation is cheap; accepted state is expensive"
- "Models Propose, Records Decide"
- Guardrail framework references: NVIDIA NeMo Guardrails, Guardrails AI, Meta
  Llama Guard, and LlamaFirewall

## Findings

No direct public-web match was found for the project's distinctive slogans or
phrases such as "Models Propose, Records Decide" or "candidate generation is
cheap; accepted state is expensive."

The audit did find adjacent work that should be cited because it overlaps the
paper's terminology or threat model:

- Shared-state LLM agent contamination: "No Attacker Needed: Unintentional
  Cross-User Contamination in Shared-State LLM Agents"
- Subagent spawn and inheritance risk: "When Child Inherits: Modeling and
  Exploiting Subagent Spawn in Multi-Agent Networks"
- Guardrail and agent-safety systems: NVIDIA NeMo Guardrails, Guardrails AI,
  Meta Llama Guard, and Meta LlamaFirewall

## Changes Made

- Added the shared-state contamination and subagent inheritance papers to
  `docs/paper_draft.md` and `docs/paper_draft.zh-CN.md`.
- Reworded the paper so "semantic contamination" is described as the local name
  for TGA's proposal-to-state failure surface, not as a claimed new global term.
- Added official Guardrails / Llama Guard / LlamaFirewall sources to the paper
  references.
- Reworded `docs/market_survey.md` and `docs/market_survey.zh-CN.md` to avoid
  overclaiming what other guardrail systems do or do not support by default.

## Remaining Risk

Public-web search cannot prove absence of plagiarism or prior art. Before a
formal submission, run a proper plagiarism/similarity checker on the final PDF
and re-check recent arXiv work in `cs.AI`, `cs.CL`, and `cs.CR`.
