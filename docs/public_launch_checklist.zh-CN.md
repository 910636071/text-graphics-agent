# 公开发布清单

英文原文：[Public Launch Checklist](./public_launch_checklist.md)。

将 `text-graphics-agent/` 拆成独立公开仓库前，按这份清单检查。

## 仓库

- [x] 选择并提交公开许可证：Apache-2.0。
- [x] 添加 `.gitignore` 和 Python package metadata。
- [ ] 确认仓库 URL，并更新 `README.md`、`README.zh-CN.md` 和 `CITATION.cff`。
- [ ] 从 Figma pitch 导出社交预览图。
- [ ] 打 `v0.1.0-paper-artifact` tag。
- [ ] 在 Zenodo 归档 release，并把 DOI 加入 `CITATION.cff`。

## 验证

- [ ] `python tests/text_graphics_agent_test.py`
- [ ] `python -m text_graphics_agent.demo`
- [ ] `python -m text_graphics_agent.benchmark`
- [x] 可选：`python -m text_graphics_agent.api_benchmark --max-scenarios 2`
- [ ] 确认 benchmark 输出与 README 一致。
- [ ] 可选：构建用于演示的 `dist/TextGraphicsAgent/TextGraphicsAgent.exe`。
- [ ] 确认没有提交生成的 cache 文件。

## 声明纪律

- [ ] 不声称 AGI。
- [ ] 不声称解决所有幻觉。
- [ ] 不声称防止所有 prompt injection。
- [ ] 保持 benchmark 描述为 deterministic closed-protocol。
- [ ] 与 LangGraph / CrewAI / OpenAI Agents SDK 的比较只能是 protocol-layer positioning，不是替代叙事。

## 论文

- [ ] 如果 `constraint-checked-state-records` 有 DOI，加入 DOI。
- [ ] 将 benchmark 输出导出为 JSONL。
- [ ] 做真实模型 baseline 后再提出经验性声明。
- [ ] 加入截图 / 多模态污染 cases。
- [ ] 加入 shared-memory contamination cases。
