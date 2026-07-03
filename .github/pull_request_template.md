## Summary / 摘要

Describe the change in one or two sentences.

用一两句话说明这次改动。

## Boundary Check / 边界检查

- [ ] Child agents still receive sanitized `TaskSpec` only. / 子 agent 仍然只接收清洗后的 `TaskSpec`。
- [ ] Proposals still enter through `AgentProposal`. / 提案仍然通过 `AgentProposal` 进入。
- [ ] State entry still passes through `ConstraintChecker`. / 状态入账仍然经过 `ConstraintChecker`。
- [ ] No raw user text is added to child context or metadata. / 没有把原始用户文本加入子 agent 上下文或 metadata。

## Verification / 验证

```powershell
python tests/text_graphics_agent_test.py
python -m text_graphics_agent.demo
python -m text_graphics_agent.benchmark
```

## Claim Discipline / 声明纪律

- [ ] Documentation avoids AGI claims. / 文档不声称 AGI。
- [ ] Documentation avoids broad safety guarantees. / 文档不做宽泛安全保证。
- [ ] Benchmark language remains scoped to deterministic closed-protocol tests. / Benchmark 表述限定在确定性闭环协议测试内。
