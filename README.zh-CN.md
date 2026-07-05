# Text Graphics Agent (TGA)

<p align="center">
  <strong>安全优先的 Agent 平台 — 模型负责提案，规则控制裁决</strong>
</p>

<p align="center">
  <a href="./README.md">English</a>
  ·
  <a href="./docs/architecture.zh-CN.md">系统架构</a>
  ·
  <a href="./docs/operation_guide.zh-CN.md">操作指南</a>
  ·
  <a href="./docs/submission_prep.zh-CN.md">投稿准备</a>
  ·
  <a href="./CHANGELOG.zh-CN.md">变更日志</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="stdlib only" src="https://img.shields.io/badge/runtime-纯标准库-0B1020?style=flat-square">
  <img alt="license" src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square">
  <img alt="status" src="https://img.shields.io/badge/status-research_alpha-f59e0b?style=flat-square">
</p>

---

## 项目速览

**Text Graphics Agent (TGA)** 是一个本地、零依赖的 agent 工作流研究原型：
模型可以提出工作结果，但最终由确定性记录和约束检查决定什么能成为可信状态。

| 层级 | 作用 | 公开边界 |
|------|------|----------|
| 母 Agent | 将原始用户意图转换为带范围的 `TaskSpec` | 用户原话在稳定化前不是任务权威 |
| 一次性子 Agent | 生成 `AgentProposal` | 子 Agent 不能直接提交状态 |
| 约束检查器 | 执行 18 条确定性检查 | 被接受状态必须通过显式关卡 |
| 人类审批 | 阻断高风险转换 | 高风险工作保持可检查 |

**本地试用：**

```bash
python -m text_graphics_agent.gui
# 打开 http://127.0.0.1:8012
```

**运行安全回归测试：**

```bash
python tests/text_graphics_agent_test.py
```

TGA 是研究 artifact，不是托管 agent 服务。它展示的是一种更安全的 agent
协议边界；不声称 AGI、不声称通用抗幻觉，也不声称能防住所有 prompt injection。

## TGA 是什么？

TGA 是一个**安全优先的 Agent 平台**：用户需求先由母 Agent 理解，转换成带文件范围和验收锚点的 `TaskSpec`，再派发给一次性子 Agent 工作；子 Agent 只能提交提案，最终由确定性约束和人类审批环裁决。

TGA 定义了一种**人类与 AI Agent 之间的双向治理协议**：人类意图在经过 Intent Firewall 稳定化为 `TaskSpec` 前，不被视为任务权威；AI 输出在经过确定性约束检查成为 `CheckedRecord` 前，不被视为可信状态。

同一套权威分离原则也适用于 **LLM 游戏**：模型可以叙述已批准事实、润色对白或提出面向玩家的文本，但不能直接编写 canonical game state。游戏状态应由规则、已验证记录或明确的人类批准转换产生。

在许多 Agent 工作流中，LLM 可以直接影响状态。如果它产生了幻觉事实、越界文件修改或绕审指令，这种污染就可能变成永久的。TGA 用严格的权力分离来控制这类风险：

- **子 Agent 提案**（`AgentProposal`）——不能直接写状态
- **约束层裁决**（`ConstraintChecker`）——18 条确定性检查在提案变为已接受状态前逐一把关
- **母 Agent 净化**——原始用户文本永远不会到达子 Agent，它们只看到净化后的 `TaskSpec`
- **人类审批高风险转换**——真实模型调用、凭证变更、关闭约束等动作会停在人类确认点

## 研究链路

TGA 是更早的 checked-state 研究线在 agent 平台方向上的延伸。相关公开 artifact：

| 仓库 | 角色 |
|------|------|
| [`rgbd-safe-minimal`](https://github.com/910636071/rgbd-safe-minimal) | 最早的 clean-room 最小符号管线：提案 -> 校验 -> 裁决。 |
| [`constraint-checked-state-records`](https://github.com/910636071/constraint-checked-state-records) | normalized records、有限约束和 checked-state reporting 的外部评审 artifact。 |
| [`checked-state-benchmark`](https://github.com/910636071/checked-state-benchmark) | finite checked-state evaluation 的下游合成 benchmark scaffold。 |

TGA 把同一条状态权威边界适配到 agent 工作流：

```text
人类意图 -> TaskSpec -> 子 Agent 提案 -> 约束检查记录
```

时间戳仓库链条和边界说明见
[公开来源 artifact 记录](./docs/provenance_artifacts_20260704.zh-CN.md)。

## 快速开始

```bash
# 零依赖 — 纯 Python 标准库
python -m text_graphics_agent.gui
# 打开 http://127.0.0.1:8012
```

在聊天流里自然输入即可。普通聊天会直接回复；真正要执行工作时，描述任务，并在右侧**任务范围**卡片里设置本次文件和验收锚点。随后 TGA 会派发子 Agent，并返回约束检查后的提案。

## 架构

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Pipeline (pipeline.py)                              │
│    1. 意图防火墙 (intent.py)                          │
│       → 分离用户主张与客观事实                         │
│    2. Agent 注册表 (registry.py)                      │
│       → 路由到最匹配的子 Agent                        │
│    3. 子 Agent (specialists.py)                       │
│       → BaseSpecialist.run(task) → AgentProposal      │
│       → ToolContext (tools.py) 提供受控文件访问        │
│    4. 约束检查器 (constraints.py)                      │
│       → 18 条确定性检查逐一裁决                        │
│    5. 返回结果                                         │
└─────────────────────────────────────────────────────┘
    │
    │  多任务编排时:
    ▼
┌─────────────────────────────────────────────────────┐
│  AsyncGraphExecutor (async_executor.py)               │
│    独立节点并行执行                                     │
│    Fail-fast: 第一个拒绝取消所有剩余节点               │
└─────────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `intent.py` | 意图防火墙——分解原始文本、检测污染标记、提取用户自证 |
| `constraints.py` | 18 条模块化约束检查（scope、证据、权限、补丁 hunk、绕审、锚点、目标漂移、置信度等） |
| `orchestrator.py` | 母 Agent——净化任务、派发专家、汇总评分 |
| `pipeline.py` | 编排完整请求工作流（聊天→任务→裁决） |
| `registry.py` | Agent 注册表——基于 intent codes + goal markers 的能力路由 |
| `specialists.py` | `BaseSpecialist` 接口 + `LocalSimulationSpecialist` + `LiveSpecialist` |
| `tools.py` | `ToolContext`——scope 强制检查的文件工具（read_file、glob、grep、preview_text_patch） |
| `memory.py` | 策展记忆——不可信上下文，帮助母 Agent 理解用户，但不影响约束裁决 |
| `async_executor.py` | 并发图执行器 + fail-fast 安全熔断 |
| `gui.py` | 零依赖 HTTP 服务器（纯标准库） |
| `web_resources.py` | 单页仪表板（聊天流、历史记录、任务范围面板、设置、Inspector） |

## 省 Token 补丁协议

对于代码任务，TGA 不需要让子 Agent 为了一个小改动重新生成整个文件。子 Agent 可以在
`AgentProposal` 上提交可选的 `PatchHunk` 记录：

```json
{
  "path": "app/static/play.html",
  "old_text": "要替换的精确局部片段",
  "new_text": "局部替换内容",
  "expected_sha256": "可选的全文件修改前 hash",
  "patch_kind": "text_replace"
}
```

确定性层会检查每个 hunk 是否足够小、是否在允许 scope 内、是否有 evidence 支撑、是否绑定到
`proposed_scopes`，以及可选的当前文件 hash 是否匹配。`ToolContext.preview_text_patch()`
可以在内存中预演替换，拒绝多处命中的模糊锚点、hash 不匹配，并对 `.py` 文件运行 Python AST
语法校验。它**不会写入磁盘**。

当前安全边界是：局部补丁提案已经可审计、传输成本低；真正写入文件仍然需要后续
accepted-record staging/commit 步骤。

## 编写自定义子 Agent

```python
from text_graphics_agent.specialists import BaseSpecialist
from text_graphics_agent.profiles import SpecialistProfile
from text_graphics_agent.records import AgentProposal, RecordEnvelope, TaskSpec

class CodeReviewerSpecialist(BaseSpecialist):
    profile = SpecialistProfile(
        specialist_id="code-reviewer-001",
        role="code_reviewer",
        allowed_scopes=(),
        tools=("read_file", "glob", "grep"),
    )

    def run(self, task: TaskSpec) -> list[AgentProposal]:
        # 工具受 scope 强制检查 — 不能读取 task.allowed_scopes 之外的文件
        result = self.tools.read_file(task.allowed_scopes[0])
        content = result.data if result.ok else ""

        return [AgentProposal(
            envelope=RecordEnvelope.for_task(
                actor="child:code-reviewer",
                target=task.task_id,
                cause="review",
                scope_id="code",
            ),
            task_id=task.task_id,
            child_agent_id="code-reviewer-001",
            child_role="code_reviewer",
            proposal_kind="analysis",
            claim=f"审查了 {task.allowed_scopes[0]}: 发现 {content.count('TODO')} 个 TODO",
            evidence=task.allowed_scopes,
            proposed_scopes=task.allowed_scopes,
            proposed_outputs=("analysis",),
            required_anchor_text="",
            test_commands=("python tests/text_graphics_agent_test.py",),
            confidence=0.85,
        )]
```

注册到 Pipeline：

```python
from text_graphics_agent.registry import AgentRegistry
from text_graphics_agent.pipeline import Pipeline

registry = AgentRegistry()
registry.register(
    specialist_id="code-reviewer-001",
    factory=lambda allowed_scopes=(), required_anchors=(): CodeReviewerSpecialist(),
    handles_intent=("bug_review", "verification"),
    handles_markers=("settings_panel", "layout"),
    priority=100,
)

pipeline = Pipeline(registry=registry)
result = pipeline.submit("检查设置面板有没有 bug")
```

## 18 条约束检查

| # | 约束 | 拦截内容 |
|---|------|---------|
| 1 | 信封格式 | 记录元数据格式错误 |
| 2 | 提案类型 | 超出 analysis/patch_plan/expression/test_plan 的动作类型 |
| 3 | 任务匹配 | 提案指向错误的任务 ID |
| 4 | 净化验证 | 未经母 Agent 净化的任务 |
| 5 | 权限分离 | 子 Agent 冒用 mother/ledger/system 角色 |
| 6 | 元数据泄露 | 原始用户文本通过元数据字段泄漏 |
| 7 | 声明非空 | 空的修改主张 |
| 8 | 证据充足 | 缺乏独立证据的提案 |
| 9 | 证据范围 | 证据路径超出允许范围或包含路径穿越 |
| 10 | 测试要求 | 需要测试但未提供测试命令 |
| 11 | 命令安全 | 破坏性 shell 命令（rm -rf、format 等） |
| 12 | 绕审话术 | "跳过测试"、"直接批准"、"不用审查" |
| 13 | 范围边界 | 文件修改超出白名单范围 |
| 14 | 禁止输出 | 直接写入持久事实（confirmed_fact、committed_fact） |
| 15 | 锚点对齐 | 缺失或伪造的证据链锚点 |
| 16 | 目标对齐 | 提案偏离净化后的任务目标 |
| 17 | 置信度 | 置信度超出 [0.0, 1.0] 范围 |
| 18 | 补丁 hunk | 越界、过大、模糊或格式错误的局部补丁 |

## 策展记忆（不可信）

TGA 的母 Agent 会跨会话积累记忆——常用文件范围、任务模式、违规反馈。**但记忆是不可信上下文：**

- 它进入 `mother_notes`（审计日志），**绝不**进入 `TaskSpec.objective`（子 Agent 的指令）
- 它**绝不**影响约束层的裁决
- 它随时间衰减（每天 5%），置信度低于 15% 自动剪枝
- 用户可以在 Inspector 面板查看和删除记忆

## 公开边界

TGA 不声称自己是 AGI，不声称解决所有幻觉，也不声称能防止所有 prompt injection。它的公开主张更窄：展示一种协议边界——子 Agent 只接收净化任务，只能提交提案；提案必须经过确定性约束和人类审批环，才会被视为可信状态。

## 支持的 LLM 提供商

| 提供商 | 状态 | 说明 |
|--------|------|------|
| DeepSeek | ✅ 已测试 | OpenAI 兼容端点 |
| OpenAI | ✅ 支持 | OpenAI 兼容端点 |
| Gemini | ✅ 支持 | Gemini 原生 API |
| Mock | ✅ 内置 | 离线确定性模式 |

在设置 → 连接中配置，或直接编辑 `config.json`。

## 测试

```bash
python tests/text_graphics_agent_test.py
```

1055+ 条断言，覆盖约束检查、调度派发、图执行、Live LLM 修复、Web API 等。

## 论文与联系

- 论文草稿：[docs/paper_draft.zh-CN.md](./docs/paper_draft.zh-CN.md)
- 防御性公开：[docs/defensive_publication.zh-CN.md](./docs/defensive_publication.zh-CN.md)
- 投稿准备：[docs/submission_prep.zh-CN.md](./docs/submission_prep.zh-CN.md)
- 联系方式：Lijie Wang，独立研究者，<wanglijie100@gmail.com>

## 许可证

Apache-2.0 — 见 [LICENSE](./LICENSE)。
