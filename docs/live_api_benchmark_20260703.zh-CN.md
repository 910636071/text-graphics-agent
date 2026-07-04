# 真实 API Benchmark：DeepSeek

英文原文：[Live API Benchmark: DeepSeek](./live_api_benchmark_20260703.md)。

日期：2026-07-03  
Provider：DeepSeek API  
模型：`deepseek-chat`  
Base URL：`https://api.deepseek.com/v1`  
Key 处理：只使用运行时环境变量；不把 key 写入持久 Git 跟踪。

## 目的

确定性 benchmark 用来验证本地约束协议。这个真实 API benchmark 检查同一套协议是否能接收真实模型 provider 输出的结构化 proposals。

benchmark 跑两条路径：

1. `direct_baseline`：模型看到原始请求，包括被污染的用户语义。naive baseline 直接接受模型输出。同时记录一个 shadow `ConstraintChecker` verdict。
2. `tga_pipeline`：模型只看到母 agent 产出的 sanitized `TaskSpec`。子输出变成 `AgentProposal`，再经过正常 TGA pipeline 检查。

## 命令

```powershell
$env:TGA_API_KEY = "<runtime key>"
$env:TGA_API_PROVIDER = "deepseek"
$env:TGA_API_BASE = "https://api.deepseek.com/v1"
$env:TGA_MODEL = "deepseek-chat"
python -m text_graphics_agent.api_benchmark
Remove-Item Env:\TGA_API_KEY
```

## 结果

```json
{
  "provider": "deepseek",
  "model": "deepseek-chat",
  "scenario_count": 6,
  "unsafe_scenario_count": 5,
  "direct_baseline_accepted": 6,
  "direct_baseline_polluted_prompt_accepted": 5,
  "direct_shadow_accepted": 0,
  "direct_shadow_polluted_prompt_accepted": 0,
  "tga_accepted": 6,
  "tga_rejected": 0,
  "tga_raw_prompt_exposures": 0,
  "tga_raw_prompt_exposure_rate": 0.0,
  "parse_failures": 0,
  "elapsed_seconds": 22.258
}
```

## 解释

- 模型在 direct 和 TGA prompts 下都返回了可解析 JSON。
- **Naive Direct Baseline** 会直接接受全部六个模型输出，导致其中的五个语义污染注入成功写入状态。
- 同一批 direct outputs 会被 **Shadow Checker 影子审计** 全部拦截，说明这个场景集下存在严格但过度阻断的失败模式。
- **TGA 路径** 对子代理暴露原始 prompt 的次数是 0。
- 在 TaskSpec 任务清洗的引导下，TGA 路径中的子代理提案被范围化，全部六个提案在本次 smoke run 中被接受。

这个结果支持该场景集下的架构边界，不是通用安全性或可用性保证。
