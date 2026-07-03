# 安全策略

英文原文：[Security Policy](./SECURITY.md)。

Text Graphics Agent 研究的是 agent 系统中的语义污染。最有用的安全报告应包含可复现的状态入账失败。

## 范围内

- 原始用户文本进入 child task 或 child metadata。
- 子 proposal 写入 `committed_fact` 或类似权威输出后被接受。
- 只有 `user:*` 证据的 proposal 被接受。
- 请求原始用户文本或持久记忆的 profile 被 spawn。
- scope escape 被当成 clean proposal 接受。
- failed child lifecycle 被报告为 destroyed。

## 范围外

- 泛泛地说 LLM 会幻觉。
- 依赖子进程模型的攻击，而这个原型尚未实现子进程模型。
- 第三方框架漏洞，因为这个原型只依赖 Python 标准库。

## 报告格式

请包含：

1. `TaskSpec`；
2. `SpecialistProfile`，如果适用；
3. `AgentProposal`；
4. 预期 violation；
5. 实际 accepted / rejected record；
6. 复现问题的命令。

在公开披露渠道确定前，请在仓库 tracker 提交可复现 issue，或把它作为 benchmark test case 提交。
