# Extraction Map

This prototype is extracted from project contracts, not copied from runtime
business logic.

## Local Project Sources

- `AGENTS.md`
  - Rules produce facts.
  - LLM expresses but does not bookkeep.
  - Client/Godot only presents.

- `docs/39-废都物语节点线转向.md`
  - Fixed action set plus text/visual presentation.
  - One-frame UI: different modes are state, not separate worlds.

- `docs/40-世界AI服务层与账号收束.md`
  - Propose-approve expression loop.
  - Budgeted expression and template fallback.
  - Human/automatic review records.

- `behavior-card-mvp/app/event_shapes.py`
  - Standard envelope discipline for event records.

- `behavior-card-mvp/app/services/review_service.py`
  - Pending, auto-passed, auto-rejected, human decision, and spot-check states.

- `behavior-card-mvp/tests/llm_expression_test.py`
  - Required-anchor judge and template fallback.

- `behavior-card-mvp/tests/play_interaction_lock_test.py`
  - UI mutations during async work must be locked.

- `verify.py`
  - The scorecard is a first-class artifact: active tests and E2E checks decide
    whether a change is real.

## Research Notes Added During Extraction

- DeepSeek-Prover-V2 shows a useful separation: a strong general model can
  decompose complex work into subgoals, while smaller/verifying components
  resolve or check those subgoals. This supports the mother-child agent split,
  but also reinforces that decomposition is not authority by itself.

- Intent-extraction decomposition work on UI trajectories separates per-screen
  summaries from final intent extraction. The same pattern maps to this project:
  raw user language and multimodal observations should first become bounded
  summaries/intent frames, then enter task planning.

## External Reference

- `910636071/constraint-checked-state-records`
  - Clean-room checked-record protocol over normalized records.
  - This folder keeps the same boundary idea but implements a new, local,
    game-agent-oriented prototype.
