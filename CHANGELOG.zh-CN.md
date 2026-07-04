# 变更日志

English version: [Changelog](./CHANGELOG.md).

## 2026-07-04 — 平台化改造

### 破坏性变更

- `gui.py` 中的 `simulate_pipeline_payload` 现在是 `pipeline.py` 中 `Pipeline.submit()` 的薄包装。函数签名不变，向后兼容。
- `make_clean_task` 新增可选参数 `memory_hints`。现有调用方不受影响。
- 许可证保持 Apache-2.0（未变更）。

### 新增模块

- **`pipeline.py`** — 编排完整请求工作流（意图→聊天→澄清→任务→子 Agent→裁决→记忆）。替代了 558 行的 `simulate_pipeline_payload` 上帝函数。
- **`specialists.py`** — `BaseSpecialist` 抽象接口 + `LocalSimulationSpecialist` + `LiveSpecialist`。标准化子 Agent 契约，支持生命周期管理和工具访问。
- **`registry.py`** — `AgentRegistry` 能力路由。子 Agent 声明可处理的 intent codes 和 goal markers，Pipeline 按评分选择最匹配的。
- **`tools.py`** — `ToolContext` 提供 scope 强制检查的 `read_file`、`glob`、`grep`。每次工具调用都检查 `task.allowed_scopes`。包含 `ToolRegistry` 支持自定义工具。
- **`memory.py`** — 策展记忆存储。母 Agent 跨会话积累客观观察（文件范围、任务模式、违规反馈）。记忆是不可信上下文——进入 `mother_notes` 但绝不进入 `TaskSpec.objective`，绝不影响约束裁决。支持置信度衰减（每天 5%）和自动剪枝。
- **`async_executor.py`** — `AsyncGraphExecutor` 线程池并发执行。独立节点并行运行；第一个失败取消所有剩余 future（保持 fail-fast）。

### 安全改进

- **意图防火墙中文覆盖**：`BYPASS_MARKERS` 从 8 条扩充到 55 条（中英文）。`USER_CLAIM_MARKERS` 从 5 条扩充到 35 条。`SCOPE_MARKERS` 改为上下文感知检测，减少"全部""所有"等常用词的误报。
- **原子意图分割**：现在处理中文标点 `！？、`，不再只处理 `，。；`。
- **`_looks_like_scope_path` bug 修复**：包含句号的自然语言句子（如 "The task objective requires..."）被误判为文件路径。现在要求必须有 `/` 或 `\`。
- **统一关键词源头**：`intent.py` 中的 `BYPASS_MARKERS`、`SCOPE_MARKERS`、`USER_CLAIM_MARKERS` 成为唯一真相源。`constraints.py`、`gui.py`、`interactive_sandbox.py` 从此处导入——不再有不同步的关键词列表。
- **`IntentDecomposer._intent_codes`**：移除"做"（太宽泛，几乎匹配所有中文句子）。移除单独的"agent"作为 `architecture_review` 触发词（改为"母 agent"、"子 agent"、"agent 架构"）。

### UI/UX 全面升级

- **聊天流界面**：首屏从工作台表单改为 ChatGPT 式聊天流。Enter 发送（Shift+Enter 换行）。任务结果以卡片形式出现在聊天流中，带"查看详情"按钮。
- **对话持久化**：所有对话保存到 `localStorage`。侧边栏显示历史列表，支持搜索。从首条用户消息自动生成标题。
- **视觉风格升级**：高对比色彩系统 + 品牌渐变（橙→琥珀→金）。聊天气泡入场动画。打字指示器。渐变 Logo 欢迎页。
- **任务范围卡片**：文件范围、验收锚点、工作区文件浏览、粘贴路径、拖入文件名匹配和会话级自动保存移动到聊天输入旁边，让每次请求都能带上明确执行边界，同时避免大表单压迫感。
- **设置页重构**：三个分区卡片（连接、默认文件范围、安全规则）。"测试连接"按钮。默认范围预设保留给重复工作流使用。
- **Inspector 切换**：右栏默认隐藏。顶栏切换按钮（👁/🔍）。Inspector 现在展示任务上下文、权限边界和记忆状态；显示状态持久化到 localStorage。
- **渐进式披露**：Composer 状态栏首次提交前隐藏。结果用可折叠 `<details>` 包裹工作流时间线和审计详情。
- **违规解释**：聊天流中为每种违规类型显示具体修改建议（10 种类型，中英文）。
- **记忆面板**：Inspector 显示策展记忆，含置信度百分比和删除按钮。标注"不可信"。

### LLM 集成改进

- **`tga_messages` prompt 重写**：7 条明确规则，确保 `proposed_outputs` 包含实际交付内容（不是描述），`evidence` 是文件路径（不是句子），`test_commands` 是真实命令。
- **`repair_messages` prompt 重写**：针对每种违规类型的具体修复指引，而非泛泛的"修复违规"。
- **`max_tokens`**：从 800 增加到 4096，避免 JSON 被截断。
- **`LiveSpecialist` 超时**：从 20 秒增加到 60 秒，适应代码生成任务。
- **空内容检查**：`call_live_llm` 现在在 LLM 返回空内容时抛出描述性错误。
- **DeepSeek 兼容性**：测试连接 prompt 包含 "json" 关键词（DeepSeek 的 `response_format: json_object` 要求）。

### 后端 API

- `GET /api/memory` — 获取策展记忆。
- `POST /api/memory` — 删除单条记忆（`{action: "delete", id: "..."}`）或清空全部（`{action: "clear"}`）。
- `POST /api/test-connection` — 测试 LLM 连通性（provider + key + model）。
- `POST /api/list-files` — 列出工作区文件供 scope 选择器使用（排除 .git、node_modules 等）。

### 其他

- 添加 `.gitignore`（config.json、memory.json、__pycache__、构建产物、临时测试文件）。
- 从 config.json 中清除 API Key（默认使用 mock provider）。
- `LICENSE`、`pyproject.toml`、`CITATION.cff` 和 README 徽章统一保持 Apache-2.0。

## 未发布（平台化之前）

- 添加 Text Graphics Agent 研究原型。
- 添加母 Agent 意图分解和净化 TaskSpec 创建。
- 添加一次性子 Agent 生命周期记录。
- 添加证据、权限、范围、锚点、测试、元数据泄露和置信度的有限约束检查。
- 添加子 Agent 角色配置的 raw-text、memory、scope、role、tool 边界。
- 添加任务图和检查点原语。
- 添加确定性污染基准测试。
- 添加论文草稿、前沿技术调研、多语言 README 和公开发布打包。
- 添加 DeepSeek live API 基准测试工具和冒烟结果文档。
- 添加中文文档镜像和中文审阅清单。
