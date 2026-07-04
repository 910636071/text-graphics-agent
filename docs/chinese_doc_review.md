# 中文文档审查记录

审查日期：2026-07-03；更新：2026-07-04（平台化改造后全量复审）。

目的：确保中文读者不需要依赖英文文档才能理解项目，同时避免中文包装比英文原文更夸张。

## 覆盖范围

| 英文文件 | 中文文件 / 处理 | 状态 |
| --- | --- | --- |
| `README.md` | `README.zh-CN.md` | 已有，已改为链接中文 docs / 贡献 / 安全说明 |
| `docs/README.md` | `docs/README.zh-CN.md` | 已补 |
| `docs/architecture.md` | `docs/architecture.zh-CN.md` | 已补 |
| `docs/paper_draft.md` | `docs/paper_draft.zh-CN.md` | 已补 |
| `docs/submission_prep.md` | `docs/submission_prep.zh-CN.md` | 已补 |
| `docs/packaging.md` | `docs/packaging.zh-CN.md` | 已补 |
| `docs/brand_kit.md` | `docs/brand_kit.zh-CN.md` | 已补 |
| `docs/market_survey.md` | `docs/market_survey.zh-CN.md` | 已补 |
| `docs/citation_audit_20260704.md` | `docs/citation_audit_20260704.zh-CN.md` | 已补 |
| `docs/live_api_benchmark_20260703.md` | `docs/live_api_benchmark_20260703.zh-CN.md` | 已补 |
| `docs/extraction_map.md` | `docs/extraction_map.zh-CN.md` | 已补 |
| `docs/public_launch_checklist.md` | `docs/public_launch_checklist.zh-CN.md` | 已补 |
| `CONTRIBUTING.md` | `CONTRIBUTING.zh-CN.md` | 已补 |
| `SECURITY.md` | `SECURITY.zh-CN.md` | 已补 |
| `CHANGELOG.md` | `CHANGELOG.zh-CN.md` | 已补 |
| `CITATION.cff` | `CITATION.zh-CN.md` | 已补中文引用说明，机器可读元数据仍保留英文 |
| `NOTICE` | `NOTICE.zh-CN` | 已补 |
| `LICENSE` | `LICENSE.zh-CN.md` | 已补中文说明；英文许可证仍是正式法律文本 |
| `.github/pull_request_template.md` | 同文件双语化 | 已补 |
| `.github/ISSUE_TEMPLATE/*.yml` | 同文件双语化 | 已补 |

## 2026-07-04 平台化改造复审

以下文档在平台化改造后已全量更新中英文版：

- `README.md` / `README.zh-CN.md` — 重写为开源版，含快速开始、自定义 Specialist 示例、17 条约束检查、任务范围说明、策展记忆说明。
- `CHANGELOG.md` / `CHANGELOG.zh-CN.md` — 新增 2026-07-04 条目，记录全部 6 个新模块、安全改进、UI/UX 升级、LLM 集成改进。
- `docs/architecture.md` / `docs/architecture.zh-CN.md` — 新增平台层（Pipeline、Registry、Specialists、Tools、Memory、AsyncExecutor）和展示层描述。
- `docs/paper_draft.md` / `docs/paper_draft.zh-CN.md` — 更新架构管线图、Intent Firewall（55+35 标记）、Clean TaskSpec（记忆注入）、Specialist Profiles（BaseSpecialist + 工具层）、Graph Executor（AsyncGraphExecutor）、Web Dashboard（聊天流）、局限、下一步实验。
- `docs/submission_prep.md` / `docs/submission_prep.zh-CN.md` — 新增 arXiv 分类、endorsement 流程、公开联系方式、材料清单和推荐请求模板；明确其为投稿操作材料，不属于技术贡献。
- `docs/operation_guide.md` / `docs/operation_guide.zh-CN.md` — 重写为聊天流界面操作指南，新增对话历史、聊天旁任务范围、设置分区、策展记忆、Live LLM 章节。
- `docs/packaging.md` / `docs/packaging.zh-CN.md` — 定位从"语义防火墙"更新为"安全优先的 Agent 平台"，补充平台能力描述。
- `docs/public_launch_checklist.md` / `docs/public_launch_checklist.zh-CN.md` — 新增平台化清单项，勾选已完成项，并同步公开声明边界。
- `docs/citation_audit_20260704.md` / `docs/citation_audit_20260704.zh-CN.md` — 记录公开网页相似性和引用补强审计，明确剩余风险和后续正式投稿前的检查要求。

## 2026-07-04 任务范围与公开文案收束复审

- 中英文 README 已对齐为“用户需求 → 母 agent 澄清/拆解 → 受控 TaskSpec → 一次性子 agent 执行 → 确定性裁决”的产品叙事。
- 中英文操作指南已把任务文件、验收锚点和工作区浏览统一到聊天旁的任务范围卡片，不再描述旧的输入区范围控件。
- 中英文架构文档和公开清单已统一为 17 条确定性检查。
- 公开文本明确不声称 AGI、不声称解决所有幻觉、不声称防止所有 prompt injection，只主张 protocol boundary / closed-protocol sanity check。
- `CONTRIBUTING.md` / `CONTRIBUTING.zh-CN.md` — 新增自定义 Specialist、工具层、i18n 贡献方向。

新增模块均有中英文代码注释和 i18n 键：
- `pipeline.py` / `specialists.py` / `registry.py` / `tools.py` / `memory.py` / `async_executor.py` — 模块 docstring 和关键注释均双语化。
- `web_resources.py` — 所有新增 UI 文本均有 zh/en i18n 键。

## 声明审查

- 中文文档没有声称 AGI。
- 中文文档没有声称解决所有幻觉。
- 中文文档没有声称防止所有 prompt injection。
- Benchmark 被限定为 deterministic / closed-protocol sanity check。
- 与 LangGraph、CrewAI、OpenAI Agents SDK、Microsoft Agent Framework 的关系被描述为 protocol layer positioning，不是替代品。
- DeepSeek API benchmark 被描述为架构边界证据，不是通用安全证明。
- Apache-2.0 中文材料只作为阅读说明，不替代英文法律文本。

## 术语统一

- `semantic contamination`：语义污染。
- `mother agent`：母 agent。
- `child agent`：子 agent。
- `disposable child-agent workflow`：一次性子 agent 工作流。
- `checked record`：检查后的记录 / checked record。
- `proposal`：提案。
- `state authority`：状态权威。
- `raw user text`：原始用户文本。
- `sanitized TaskSpec`：清洗后的 `TaskSpec`。

## 审查结论

中文材料已经能覆盖英文对外材料的主路径。

在 2026-07-03 晚间追加的评审中：
1. 模块化约束系统 (`Constraint` 类重构) 的设计在中英文 README、架构说明 (`architecture.md` / `architecture.zh-CN.md`) 和调研报告 (`market_survey.md` / `market_survey.zh-CN.md`) 中均已正确对齐。
2. 任务图执行引擎 (`GraphExecutor` 运行器) 的实现细节、Fail-Fast 安全中止原则已完全同步并进行了测试。
3. 新增了本地交互式体验沙箱 (`interactive_sandbox.py`) 提供了一个零配置门槛 of REPL 终端，在中英文 README 的 Repository Map 以及快速开始命令中均已完成了对齐说明。
4. 引入了与业界前沿 LLM 安全防御与 Guardrail 框架（NVIDIA NeMo Guardrails, Guardrails AI, Meta Llama Guard）的详细对比分析，并完成了中英文市场调研报告（`market_survey`）和论文草稿（`paper_draft`）中的同步更新与对齐。
5. 评估了将 Tkinter 传统 GUI 重构为现代 Web 演示 Dashboard（以 socketserver 暴露 HTTP 接口，渲染基于玻璃拟态的单页 HTML/CSS/JS）。该设计免除了对任何外部 Node.js 或前端工程框架 of 依赖，通过网页内嵌交付，在保持单文件便携发布（EXE 编译安全）的同时，极大地拔高了可视化的展示质感与交互体验。
6. 实现了基于本地 `config.json` 的 API 密钥与 Allowed Scopes 表单配置面板，在保障 API 凭证本地安全隔離（已同步更新 `.gitignore`）的前提下，达成了开箱即用的 Web 交互配置持久化。
7. **设计了零依赖的通用大模型 API 适配层 (支持 Gemini AI Studio 和 OpenAI 兼容端点)**，成功在交互式 Playground 实现了“启用真实大模型测试 (Live LLM Defender Test)”的勾选运行。一旦检测到本地密钥，用户可在前端实时执行与真实 LLM 的 Prompt 注入攻防博弈，并在网页渲染审计 ScoreCard，全面脱离了特定宠物项目的耦合。
8. 增加了可视化规则准入开关（点击 Checker ⚖️ 节点）和 SDK 集成代码一键复制功能，并在 `tests/` 下编写了对应的规则动态旁路自适应单测。
9. 验证没有引入过度宣传，术语对齐良好。

后续公开前还需要补：

1. 仓库 URL 已确认为 `910636071/text-graphics-agent-release`；如后续变更，需要同步更新中英文 README、`pyproject.toml` 与 `CITATION.cff`。
2. 如果许可证或公开署名策略变更，`LICENSE.zh-CN.md` 和 `CITATION.zh-CN.md` 必须同步更新。
3. 公开发布必须从干净的 release 导出或独立仓库推送，不能把私有父仓库历史直接公开。
4. 如生成对外审查包，必须在本轮文档变更后重新打包，不能沿用旧 zip。
