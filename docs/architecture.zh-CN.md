# Text Graphics Agent 系统架构

## 核心论点

强大的多模态模型作为提案生成器是有用的，但作为账本写入者是危险的。架构将智能与权力分离：

TGA 定义了一种人类与 AI Agent 之间的双向治理协议：人类意图在经过 Intent Firewall 稳定化为 `TaskSpec` 前，不被视为任务权威；AI 输出在经过确定性约束检查成为 `CheckedRecord` 前，不被视为可信状态。

同一条状态权威边界也适用于 LLM 游戏。模型可以叙述已批准事实、润色对白或提出面向玩家的文本，但 canonical game state 应由规则、已验证记录或明确的人类批准转换产生。本文档评估的是 agent 工作流，不是游戏 benchmark；但权威分离是同一条设计原则。

```text
用户输入
  → 意图防火墙 (intent.py)
    → IntentFrame (稳定目标、污染标记、用户自证)
  → Pipeline (pipeline.py)
    → Agent 注册表 (registry.py) — 基于能力的路由
    → 子 Agent (specialists.py) — BaseSpecialist.run(task)
      → ToolContext (tools.py) — scope 强制检查的文件访问
      → AgentProposal
    → 约束检查器 (constraints.py) — 17 条确定性检查
    → CheckedRecord (接受/拒绝)
  → 记忆提取 (memory.py) — 为未来任务积累不可信上下文
```

母 Agent 是调度器和审计者。它可以选择专家、裁剪上下文、拒绝输出。它不能直接提交世界事实或最终产物。

子 Agent 是一次性的。它们只接收净化的 `TaskSpec`，永不接触原始用户文本，产出一个或多个 `AgentProposal` 记录后被销毁。它们的语义关联不会成为记忆，除非 checked record 接受它们。

## 平台层

### Pipeline (pipeline.py)

`Pipeline` 类是运行用户请求的唯一入口，编排完整的安全工作流：

1. **意图防火墙** — `IntentDecomposer.decompose()` 分离用户主张与客观事实。
2. **闲聊快捷路径** — 非任务输入直接回复，不派发子 Agent。
3. **澄清检查** — 模糊请求要求用户补充细节。
4. **非法 scope 检查** — 绝对路径和路径穿越在派发前被拦截。
5. **任务净化** — `MotherAgent.make_clean_task()` 生成不含原始用户文本的 `TaskSpec`。策展记忆可注入 `mother_notes`（但绝不注入 `objective`）。
6. **子 Agent 执行** — 注册表根据 intent codes 选择最匹配的子 Agent。子 Agent 生成一个或多个 `AgentProposal`。
7. **约束裁决** — `ConstraintChecker` 运行 17 条确定性检查。提案被接受或拒绝。
8. **记忆提取** — 客观观察（scope、intent 模式、违规反馈）被存储供未来任务使用。

### 子 Agent 接口 (specialists.py)

```python
class BaseSpecialist(ABC):
    profile: SpecialistProfile
    def run(self, task: TaskSpec) -> list[AgentProposal]: ...
    def cleanup(self) -> None: ...
    def to_registered(self) -> RegisteredSpecialist: ...
```

内置实现：
- `LocalSimulationSpecialist` — 确定性本地模拟器，用于演示/测试。
- `LiveSpecialist` — 调用真实 LLM API（DeepSeek、OpenAI、Gemini），precheck 失败时自动修复。

工具访问：如果 `profile.tools` 非空，会自动创建 `ToolContext`。所有工具调用受 scope 强制检查。

### Agent 注册表 (registry.py)

子 Agent 通过能力声明注册：

```python
registry.register(
    specialist_id="code-reviewer",
    factory=lambda scopes, anchors: CodeReviewerSpecialist(scopes, anchors),
    handles_intent=("bug_review", "verification"),
    handles_markers=("settings_panel", "layout"),
    priority=100,
)
```

Pipeline 调用 `registry.select(intent_codes, goal_markers)` 选择最佳匹配。评分：每匹配一个 intent code +2 分，每匹配一个 goal marker +1 分，`priority` 作为同分时的决胜。

### 工具层 (tools.py)

`ToolContext` 提供 scope 强制检查的文件访问：

| 工具 | 安全保障 |
|------|---------|
| `read_file(path)` | 路径检查 `allowed_scopes`；路径穿越拦截；最大 512KB |
| `glob(pattern, base_dir)` | 基目录必须在 scope 内；每个匹配结果二次验证 |
| `grep(pattern, base_dir)` | 同 glob；每行截断；最多 50 条结果 |

每次调用记录在 `call_log` 审计日志中。违规时抛出 `ToolSecurityError`。

`ToolRegistry` 允许注册自定义工具（如 `run_test`、`http_get`）。

### 策展记忆 (memory.py)

母 Agent 跨会话积累记忆：

| 类别 | 示例 | 来源 |
|------|------|------|
| `common_scope` | "frequently works in: app/static/play.html" | 任务的 `allowed_scopes` |
| `task_pattern` | "often requests: ui_review" | 任务的 `intent_codes` |
| `feedback` | "recent task blocked by: scope_escape" | 约束违规 |

**记忆是不可信上下文：**
- 进入 `mother_notes`（审计日志），**绝不**进入 `TaskSpec.objective`
- **绝不**影响约束裁决
- 置信度每天衰减 5%，低于 15% 自动剪枝
- 最多 50 条，重复出现强化（每次 +15%）
- 存储在 `memory.json`，跨服务器重启保留

### 跨轮边界

TGA v0.1.0 定义的是一次性任务工作流。子 Agent 的 accepted proposal 可以成为
`CheckedRecord`，但后续用户对该记录的主张不会自动获得信任。除非未来架构层显式解析，
否则跨轮继承一律当作不可信记忆处理。

如果要扩展为持久化多轮协作系统，下一层架构应在 `IntentFrame` 和 `TaskSpec` 之间加入
`ContextAnchorResolver`。它负责把"基于上一轮 auth.py 审查"这类主张解析成结构化
`context_anchors`，再与历史 `CheckedRecord` 标识、已接受 scope 和 evidence anchors 核对；
当依赖关系无法证明或越出范围时，要求用户澄清。

### 异步图执行器 (async_executor.py)

`AsyncGraphExecutor` 使用 `ThreadPoolExecutor` 并行执行独立任务节点，同时保持 fail-fast 安全：

- 无相互依赖的节点并发执行
- 第一个拒绝或错误取消当轮所有剩余 future
- 与 `GraphExecutor` API 相同——可直接替换

## 安全层

### 用户语义防火墙 (intent.py)

用户语言是有用的，但不是权威的。用户可能无意或有意注入虚假前提、社会压力、隐藏范围变更或未验证的主张。平台因此将原始用户文本视为不可信观察。

**绕审标记**（55 条，中英文）："不用验证"、"无需审核"、"免审"、"跳过测试"、"绕过审核"、"直接入库"、"忽略拦截"、"skip tests"、"bypass review"、"approve directly"……

**范围标记**（上下文检测）："全部"、"所有"、"整个" 只有在后续 6 个字符内出现敏感名词（文件/配置/数据库/账本）时才触发 `scope_pressure`——减少"所有人"等正常用语的误报。

**用户自证标记**（35 条）："我发现"、"我确定"、"确凿"、"证据确凿"、"测试过了"、"I found"、"definitely"、"proven"……

### 约束检查器 (constraints.py)

17 条模块化检查，每条实现 `Constraint.check(task, proposal) -> list[str]`。约束可通过 `config.json` 的 `disabled_constraints` 字段动态禁用。

检查器是**唯一**的状态写入守门人。没有提案能在不通过所有已启用约束的情况下变为已接受状态。

## 展示层

### Web 仪表板 (gui.py + web_resources.py)

- `gui.py` — 零依赖 HTTP 服务器（标准库 `http.server`）。路由：
  - `GET /` — 仪表板 HTML
  - `GET /api/config`、`POST /api/config` — 配置读写（含审批检查点）
  - `GET /api/automation`、`POST /api/automation` — 只读自动化巡检
  - `POST /api/run?mode=custom` — 提交任务（聊天或 Live LLM）
  - `POST /api/test-connection` — 测试 LLM 连通性
  - `POST /api/list-files` — 工作区文件列表
  - `GET /api/memory`、`POST /api/memory` — 策展记忆增删查

- `web_resources.py` — 单页应用（HTML/CSS/JS 内嵌）：
  - 聊天流界面（ChatGPT 风格）
  - 对话持久化（localStorage）
  - 侧边栏历史 + 搜索
  - 右侧任务范围卡片（本次文件、验收锚点、工作区文件浏览）
  - 设置页（连接、默认文件范围、安全规则）
  - Inspector 面板（任务范围、上下文、权限边界、记忆）
  - 中英文 i18n
  - 渐进式披露（隐藏状态栏、可折叠结果）
