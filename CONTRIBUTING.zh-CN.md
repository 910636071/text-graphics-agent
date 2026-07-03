# 贡献指南

英文原文：[Contributing](./CONTRIBUTING.md)。

Text Graphics Agent 当前是研究原型。贡献有价值的前提是守住项目核心边界：

> 模型负责提案，记录负责裁决。

## 适合上手的贡献

- 向 `benchmark.py` 增加确定性污染场景。
- 为 profile、lifecycle 或 metadata leakage 检查增加测试。
- 改进文档，但不扩大安全声明。
- 增加 adapter，同时确保原始用户文本不进入子 agent 上下文。
- 将 benchmark 输出导出为论文表格可用的 JSONL records。

## 非目标

请避免以下贡献：

- 让子 agent 接收原始用户文本；
- 让子 agent 直接写 committed facts；
- 默认加入子 agent 持久记忆；
- 用“再问另一个 LLM 判断”替代有限检查；
- 声称项目解决所有幻觉或 prompt-injection 风险。

## 本地检查

```powershell
python tests/text_graphics_agent_test.py
python -m text_graphics_agent.demo
python -m text_graphics_agent.benchmark
```

## Pull Request 清单

- 改动有确定性测试或 benchmark scenario 覆盖。
- 新的子 agent 路径会产出 `AgentProposal` records。
- 新的状态入口路径会通过 `ConstraintChecker`。
- 文档不夸大安全性，也不声称 AGI 能力。
- 对外文案保持项目与泛 multi-agent chat orchestration 的区别。
