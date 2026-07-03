# Contributing

Chinese version: [贡献指南](./CONTRIBUTING.zh-CN.md).

Text Graphics Agent is currently a research prototype. Contributions are useful
when they preserve the project's core boundary:

> Models propose. Records decide.

## Good First Contributions

- Add deterministic contamination scenarios to `benchmark.py`.
- Add tests for profile, lifecycle, or metadata leakage checks.
- Improve documentation without expanding the safety claim.
- Add adapters that keep raw user text out of child context.
- Export benchmark outputs as JSONL records for paper tables.

## Non-goals

Please avoid contributions that:

- let child agents receive raw user text;
- let child agents write committed facts directly;
- add persistent child memory by default;
- replace finite checks with "ask another LLM to judge";
- claim the project solves all hallucination or prompt-injection risks.

## Local Checks

```powershell
python tests/text_graphics_agent_test.py
python -m text_graphics_agent.demo
python -m text_graphics_agent.benchmark
```

## Pull Request Checklist

- The change is covered by a deterministic test or benchmark scenario.
- Any new child-agent path produces `AgentProposal` records.
- Any new state entry path passes through `ConstraintChecker`.
- Documentation does not overclaim safety or AGI capability.
- Public-facing copy keeps the project distinct from generic multi-agent chat
  orchestration.
