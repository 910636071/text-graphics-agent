# v0.2.0 实现风险登记，2026-07-04

英文原文：[Implementation Risk Register for v0.2.0](./implementation_risk_register_20260704.md)。

这份登记吸收 `v0.1.0` 公开审查 artifact 之后的实现层评审意见。它不会改变已经发布的
`v0.1.0` tag。它记录的是：在对 `v0.2.0` 作出更强实现边界声明之前，哪些问题不能忘。

## 优先级

| 优先级 | 风险 | 当前 v0.1.0 事实 | v0.2.0 动作 |
| --- | --- | --- | --- |
| P1 | Evidence provenance 缺口 | 当前 evidence 主要是路径字符串，并检查 scope 和路径穿越；checker 还不能证明 claim 确实来自被引用文件内容。 | 增加 evidence provenance records：`path`、`sha256`、可选 `snippet_hash` 和 `tool_call_id`。文件派生 evidence 必须引用 provenance。 |
| P1 | Clean 请求误杀 | 现有 benchmark 更强于污染拦截，弱于 clean acceptance；`bench-clean-patch` 只有一个正例。 | 增加 clean acceptance suite，覆盖明确 scope 内的合法宽请求，例如“这个文件里的所有函数”或“整个允许模块”。单独报告 false-positive rate。 |
| P1 | 写工具事务边界 | 内置 `ToolContext` 只有读工具（`read_file`、`glob`、`grep`）。半提交风险在 v0.1.0 不活跃，但一旦加入写工具就会变成关键问题。 | 在加入 `write_file`、`run_command` 或 patch 工具之前，引入 staging area。只有 `CheckedRecord.accepted == true` 才能提交；拒绝或取消的 run 必须丢弃 staged effects。 |
| P2 | Intent firewall 召回缺口 | 第一阶段是确定性 marker/rule。这个选择是有意的，但比喻式绕审语言可能召回不到。 | 增加可选语义召回作为非权威提示层。Embedding 或 classifier 只能提高警觉或触发澄清，不能绕过确定性约束。 |
| P2 | Memory 衰减语义 | 策展记忆是不可信上下文，不影响 constraints。物理时间衰减适合弱提示，不适合未来安全策略。 | 如果未来 memory 用于安全路由，加入基于 turn/event 的 retention，并把安全反馈保留和普通偏好衰减分开。 |
| P2 | 本地工作台服务器边界 | GUI 使用标准库本地 server 和 `ThreadingMixIn`，不是 CGI，也不是生产 Web 栈。 | 继续标注为 local research workbench。若演示中频繁使用 live model call，再加入请求超时、取消或小型 job queue。 |
| P3 | 多模态 evidence 扩展 | 当前 constraints 面向文本和路径。未来截图/OCR case 可能通过图像派生 evidence 携带 prompt 文本或隐藏数据。 | 加入多模态 evidence 前，先扩展 provenance 到图片路径、OCR 文本和派生 feature records。Base64 图片 payload 不应成为未检查 evidence。 |

## v0.1.0 非目标

- 不声称事务性写工具安全；v0.1.0 没有内置写工具。
- 不声称 semantic recall 或 embedding-based intent detection。
- 不声称生产级 Web server hardening。
- 不声称多模态 evidence safety。

## 建议的 v0.2.0 最小切片

最小可信的 v0.2.0 hardening pass 应包含：

1. Evidence provenance records 和测试。
2. Clean acceptance benchmark cases，并报告 false-positive rate。
3. 在任何写能力工具加入之前，先建立 documented staging contract。

其他内容可以留作未来工作，直到这三项完成。
