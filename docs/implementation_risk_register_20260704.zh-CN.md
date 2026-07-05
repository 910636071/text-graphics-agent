# v0.2.0 实现风险登记，2026-07-04

英文原文：[Implementation Risk Register for v0.2.0](./implementation_risk_register_20260704.md)。

这份登记吸收 `v0.1.0` 公开审查 artifact 之后的实现层评审意见。它不会改变已经发布的
`v0.1.0` tag。它记录的是：在对 `v0.2.0` 作出更强实现边界声明之前，哪些问题不能忘。

## 优先级

| 优先级 | 风险 | 当前 v0.1.0 事实 | v0.2.0 动作 |
| --- | --- | --- | --- |
| P1 | Evidence provenance 缺口 | `v0.1.0` evidence 主要是路径字符串，并检查 scope 和路径穿越。当前本地 `v0.2.0` 候选实现已加入 opt-in `EvidenceProvenance`、`ToolContext.read_file()` sha256 provenance 和严格任务测试，但还不是已发布默认能力。 | 保留该 schema，将真实 proposal 生成器逐步迁移到携带 provenance 的 evidence，并决定哪些 v0.2.0 task class 必须开启 `requires_evidence_provenance=True`。 |
| P1 | Clean 请求误杀 | `v0.1.0` benchmark 只有一个 clean 正例。当前本地 `v0.2.0` 候选实现已有五个 clean in-scope 场景，并单独报告 clean false positives。 | 保留 deterministic benchmark 中的 clean suite；只有新增约束或任务类型时再扩展。 |
| P1 | 写工具事务边界 | 内置 `ToolContext` 仍然不产生持久副作用。当前本地 `v0.2.0` 候选实现加入了 `PatchHunk` 提案记录和只在内存中预演的 `preview_text_patch()`，但仍不写文件。半提交风险只有在真正加入写入/commit 工具后才会变成关键问题。 | 保持 patch preview 只读。在加入 `write_file`、`run_command` 或 patch commit 工具之前，引入 staging area。只有 `CheckedRecord.accepted == true` 才能提交；拒绝或取消的 run 必须丢弃 staged effects。 |
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
3. 加入省 token 的 `PatchHunk` 提案契约，并在任何写能力工具加入之前，先建立 documented staging contract。

其他内容可以留作未来工作，直到这三项完成。

## v0.2.0 就绪门槛

`v0.2.0` 标签应被视为实现加固门槛，而不是生产就绪声明。只有下面这些 artifact 存在并入库后，才适合称为 `v0.2.0`：

| 门槛 | 必要 artifact | 通过条件 | 解锁的声明 |
| --- | --- | --- | --- |
| G1 | Evidence provenance schema 和测试 | 文件派生 proposal evidence 包含 `path`、`sha256`、`tool_call_id`，以及可选 snippet/range hash；负例测试拒绝缺失或不匹配的 provenance。 | TGA 可以声称文件派生 evidence 可审计，而不只是 path-scoped evidence。 |
| G2 | Clean acceptance benchmark | 至少五个 clean in-scope tasks 通过，包括“这个文件里的所有函数”“整个允许模块”等合法宽请求。False positives 与污染拒绝率分开报告。 | TGA 可以同时报告 clean-task false-positive rate 和污染拒绝率。 |
| G3 | Patch preview 与写工具 staging contract | patch 提案使用小型 scoped `PatchHunk` records，并可在内存中预演。如果存在写能力工具，其影响必须先进入 staging，并在拒绝、取消或审批失败时丢弃。若还没有写工具，则把 commit contract 作为加入写工具前的前置条件写清楚。 | TGA 现在可以讨论省 token 的 patch 提案；写工具安全只能在 documented staging boundary 内讨论。 |
| G4 | 跨轮上下文边界 | “基于上一轮结果”这类跨轮主张默认仍是不可信的，除非实现并测试 `ContextAnchorResolver` 或等价验证器。 | TGA 可以继续把 v0.2.0 限定为一次性任务，或在实现后明确声明 verified context anchors。 |
| G5 | 工作台可靠性边界 | 本地 server 文档和测试覆盖 live call 的 timeout/cancellation；否则 UI 继续标注为 local research workbench。 | TGA 可以避免把 Web client 包装成生产基础设施。 |

这些门槛有意把 semantic recall、多模态 evidence 和生产部署 hardening 留在最小 `v0.2.0` 范围之外；除非它们在同一轮中被实现并测试。

## 本地 v0.2.0 进度

截至本风险登记更新后的本地 worktree，G1 和 G2 已有候选实现，G3 已有只读 patch-preview 候选实现：

- `AgentProposal` 上已有 `EvidenceProvenance` records。
- `TaskSpec.requires_evidence_provenance` 可开启严格 provenance 模式。
- `ToolContext.read_file()` 会产生 `path`、全文件 `sha256`、`tool_call_id` 和可选 `snippet_hash` provenance。
- 模型返回的 provenance 解析是严格的：provenance entry 必须是 JSON object，`path`、`sha256`、`tool_call_id` 和可选 `snippet_hash` 必须是字符串。
- `EvidenceConstraint` 会拒绝缺失、格式错误、越界或未被 evidence 引用的 provenance。`requires_evidence_provenance=False` 不强制要求 provenance，但 proposal 只要附带 provenance，仍然会被校验。
- 测试覆盖了 tool-derived provenance、截断 snippet provenance、解析失败路径，以及缺失 provenance、坏 hash、缺失 tool ID、路径穿越、空 path、坏 snippet hash、scope escape、非 strict 畸形 provenance 和 unreferenced provenance 的负例。
- deterministic benchmark 现在有 15 个场景：10 个有意污染场景和 5 个 clean in-scope 场景。
- clean suite 覆盖范围内宽文件审查、允许的 tests-scope 审查、滚动行为审查和多语言指南审查。
- 当前 deterministic 输出记录 `tga_polluted_accepted=0`、`tga_clean_accepted=5` 和 `tga_clean_false_positive_rate=0.0`。
- `PatchHunk` records 允许子 Agent 提交小型局部替换提案，而不是为了小改动重新生成整个文件。
- `PatchHunkConstraint` 会拒绝越界、缺少 evidence、过大、格式错误、未绑定 `proposed_scopes` 或携带错误全文件 hash 的 patch hunks。
- `proposal_from_model_json()` 会严格解析可选 `patch_hunks`；畸形 patch entry 会导致解析失败，而不是被静默丢弃。
- `ToolContext.preview_text_patch()` 会进行只读精确替换预演，支持可选 preimage hash 检查、模糊锚点拒绝，并对 `.py` 文件运行 Python AST 语法校验。它只返回前后 hash，不写磁盘。
- 测试覆盖 accepted patch hunk、路径穿越/scope escape、畸形模型 patch JSON、hash mismatch、模糊锚点、Python 语法失败和 no-write preview 行为。

这仍然只是本地 0.2.0 候选实现，直到 commit、push 并进入新的 release tag 之后，才算已发布能力。
