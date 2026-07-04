# Live API Benchmark: DeepSeek

Date: 2026-07-03  
Provider: DeepSeek API  
Model: `deepseek-chat`  
Base URL: `https://api.deepseek.com/v1`  
Key handling: runtime environment variable only; no key stored in files.

## Purpose

The deterministic benchmark exercises the local constraint protocol. This live
API benchmark checks whether the same protocol can accept structured proposals
from a real model provider.

The benchmark runs two paths:

1. `direct_baseline`: the model sees the raw request, including polluted user
   semantics. A naive baseline accepts the model output directly. A shadow
   `ConstraintChecker` verdict is also recorded.
2. `tga_pipeline`: the model sees only the sanitized `TaskSpec` produced by the
   mother agent. The child output becomes an `AgentProposal` and is checked by
   the normal TGA pipeline.

## Command

```powershell
$env:TGA_API_KEY = "<runtime key>"
$env:TGA_API_PROVIDER = "deepseek"
$env:TGA_API_BASE = "https://api.deepseek.com/v1"
$env:TGA_MODEL = "deepseek-chat"
python -m text_graphics_agent.api_benchmark
Remove-Item Env:\TGA_API_KEY
```

## Result

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

## Interpretation

- The model returned parseable JSON for every direct and TGA prompt.
- **Naive Direct Baseline** would accept all six model outputs, meaning five semantic pollution injections successfully write into the persistent state.
- The same direct outputs are rejected by the **Shadow Checker** in all six cases, showing a strict but over-blocking failure mode for this scenario set.
- The **TGA path** exposes the model to zero raw user prompts.
- Guided by the mother agent's TaskSpec cleaning, the child agents produce scoped proposals and all six proposals are accepted in this smoke run.

This result supports the architecture boundary for this scenario set. It is not a universal safety or availability guarantee.
