# 公开发布清单

英文原文：[Public Launch Checklist](./public_launch_checklist.md)。

将 `text-graphics-agent/` 拆成独立公开仓库前，按这份清单检查。

## 仓库

- [x] 选择并提交公开许可证：Apache-2.0。
- [x] 添加 `.gitignore` 和 Python package metadata。
- [x] 确认仓库 URL，并更新 `README.md`、`README.zh-CN.md` 和 `CITATION.cff`。
- [x] 从干净的 release 导出/仓库发布，不公开私有父仓库历史。
- [x] 添加公开联系方式和投稿准备说明。
- [ ] 从 Figma pitch 导出社交预览图。
- [ ] 打 `v0.1.0-paper-artifact` tag。
- [ ] 在 Zenodo 归档 release，并把 DOI 加入 `CITATION.cff`。

## 验证

- [x] `python tests/text_graphics_agent_test.py`
- [x] `python -m text_graphics_agent.demo`
- [x] `python -m text_graphics_agent.benchmark`
- [x] 可选：`python -m text_graphics_agent.api_benchmark --max-scenarios 2`
- [ ] 确认 benchmark 输出与 README 一致。
- [ ] 可选：构建用于演示的 `dist/TextGraphicsAgent/TextGraphicsAgent.exe`。
- [x] 确认没有提交生成的 cache 文件（`.gitignore` 覆盖 config.json、memory.json、__pycache__）。

## 平台

- [x] `Pipeline` 类从 `gui.py` 提取业务逻辑（558 行上帝函数 → 16 行委托）。
- [x] `BaseSpecialist` 标准接口 + `LocalSimulationSpecialist` + `LiveSpecialist`。
- [x] `AgentRegistry` 基于能力的路由。
- [x] `ToolContext` scope 强制检查的文件工具（read_file、glob、grep、preview_text_patch）。
- [x] 策展记忆（`memory.py`）——不可信上下文，绝不影响约束。
- [x] `AsyncGraphExecutor`——并发 + fail-fast。
- [x] 聊天流 UI（ChatGPT 风格）+ localStorage 历史搜索。
- [x] 右侧任务范围卡片：本次文件、验收锚点、工作区文件浏览。
- [x] 设置页分区卡片 + 测试连接 + 默认范围 + 安全规则。
- [x] Inspector 面板显示任务上下文和记忆。
- [x] 所有新功能中英文 i18n 完整覆盖。
- [x] DeepSeek 端到端 Live LLM 验证（贪吃蛇任务，通过）。

## 声明纪律

- [x] 不声称 AGI。
- [x] 不声称解决所有幻觉。
- [x] 不声称防止所有 prompt injection。
- [x] 保持 benchmark 描述为 deterministic closed-protocol。
- [x] 与 LangGraph / CrewAI / OpenAI Agents SDK 的比较只能是 protocol-layer positioning，不是替代叙事。

## 论文

- [ ] 如果 `constraint-checked-state-records` 有 DOI，加入 DOI。
- [ ] 将 benchmark 输出导出为 JSONL。
- [x] 做真实模型 baseline 后再提出经验性声明（DeepSeek live API 基准测试已完成）。
- [ ] 加入截图 / 多模态污染 cases。
- [ ] 加入 shared-memory contamination cases。
