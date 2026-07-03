# 抽取映射

英文原文：[Extraction Map](./extraction_map.md)。

这个原型是从项目契约里抽取出来的，不是复制游戏运行时业务逻辑。

## 本地项目来源

- `AGENTS.md`
  - 规则产生事实。
  - LLM 负责表达，不负责记账。
  - 客户端 / Godot 只负责表现。

- `docs/39-废都物语节点线转向.md`
  - 固定动作集加文本 / 视觉表现。
  - 单帧 UI：不同模式是状态，不是多个独立世界。

- `docs/40-世界AI服务层与账号收束.md`
  - propose-approve 表达环。
  - 有预算的表达生成和模板兜底。
  - 人工 / 自动审查记录。

- `behavior-card-mvp/app/event_shapes.py`
  - 事件记录的标准信封纪律。

- `behavior-card-mvp/app/services/review_service.py`
  - pending、auto-passed、auto-rejected、human decision 和 spot-check 状态。

- `behavior-card-mvp/tests/llm_expression_test.py`
  - 必需锚点评测和模板回退。

- `behavior-card-mvp/tests/play_interaction_lock_test.py`
  - 异步工作期间 UI mutation 必须锁定。

- `verify.py`
  - scorecard 是一等产物：活跃测试和 E2E 检查决定改动是否真实。

## 抽取期间补充的研究笔记

- DeepSeek-Prover-V2 展示了一种有用分离：强通用模型可将复杂工作拆成子目标，较小或验证组件负责解决 / 检查子目标。这支持母子 agent 拆分，也提醒我们：拆解本身不等于权威。

- UI trajectory 的 intent-extraction decomposition 工作把每屏摘要和最终意图抽取分开。这个模式同样适用于本项目：原始用户语言和多模态观察应该先成为有界 summary / intent frame，再进入任务规划。

## 外部参考

- `910636071/constraint-checked-state-records`
  - 归一化记录上的 clean-room checked-record 协议。
  - 本文件夹保留同一个边界思想，但实现的是新的、本地的、偏 game-agent 的原型。
