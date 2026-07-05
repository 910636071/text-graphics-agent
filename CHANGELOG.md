# Changelog

Chinese version: [变更日志](./CHANGELOG.zh-CN.md).

## 0.2.0 — Evidence and Live-Workflow Candidate

### Added

- Added file-derived `EvidenceProvenance` records with full-file `sha256`,
  optional `snippet_hash`, and `tool_call_id`.
- Added strict provenance validation for supplied provenance, plus optional
  `TaskSpec.requires_evidence_provenance` enforcement.
- Expanded the deterministic benchmark to 15 scenarios: 10 polluted cases and
  5 clean in-scope cases, with clean false-positive metrics reported
  separately.
- Added live chat routing for non-authoritative casual conversation when a
  provider key is configured. Chat replies do not create `TaskSpec`s, dispatch
  child agents, or produce `CheckedRecord`s.
- Added token-efficient `PatchHunk` proposal records, strict `patch_hunks`
  model-output parsing, patch-hunk constraint checks, and
  `ToolContext.preview_text_patch()` for in-memory exact replacement previews.
- Added `docs/test_reports/` with v0.2.0 candidate test reports in English and
  Chinese.
- Added `examples/snake_game.html` as a reviewed local functional-acceptance
  artifact. It is not evidence of write-capable child-agent execution.

### Boundaries

- This is still a research prototype and public review artifact, not a
  production-ready agent operating system.
- DeepSeek Snake is recorded as proposal smoke only; playable-game acceptance
  was performed on the local example artifact.
- G3 has read-only patch preview coverage, but write-tool staging and
  accepted-record commit semantics are not completed in this release.

## 2026-07-04 — Platform Transformation

### Breaking Changes

- `simulate_pipeline_payload` in `gui.py` is now a thin delegate to `Pipeline.submit()` in `pipeline.py`. The function signature is unchanged for backward compatibility.
- `make_clean_task` now accepts an optional `memory_hints` parameter. Existing callers are unaffected.
- License remains Apache-2.0 (no change).

### New Modules

- **`pipeline.py`** — Orchestrates the full request workflow (intent → chat → clarification → task → specialist → verdict → memory). Replaces the 558-line `simulate_pipeline_payload` god-function.
- **`specialists.py`** — `BaseSpecialist` abstract interface + `LocalSimulationSpecialist` + `LiveSpecialist`. Standardizes the child-agent contract with lifecycle management and tool access.
- **`registry.py`** — `AgentRegistry` with capability-based routing. Specialists declare which intent codes and goal markers they handle; the pipeline scores and selects the best match.
- **`tools.py`** — `ToolContext` with scope-enforced `read_file`, `glob`, `grep`. Every tool call is checked against `task.allowed_scopes`. Includes `ToolRegistry` for custom tools.
- **`memory.py`** — Curated memory store. The mother agent accumulates objective observations (scopes, intent patterns, violation feedback) across sessions. Memory is untrusted context — it enters `mother_notes` but never `TaskSpec.objective` and never affects constraint decisions. Features confidence decay (5%/day) and auto-pruning.
- **`async_executor.py`** — `AsyncGraphExecutor` with thread-pool concurrency. Independent task nodes run in parallel; first failure cancels all remaining futures (fail-fast preserved).

### Security Improvements

- **Intent Firewall Chinese coverage**: `BYPASS_MARKERS` expanded from 8 → 55 entries (Chinese + English). `USER_CLAIM_MARKERS` expanded from 5 → 35. `SCOPE_MARKERS` now uses context-aware detection to reduce false positives on common words like "全部" and "所有".
- **Atomic intent splitting**: Now handles Chinese punctuation `！？、` in addition to `，。；`.
- **`_looks_like_scope_path` bug fix**: Natural language sentences with periods (e.g. "The task objective requires...") were misidentified as file paths. Now requires `/` or `\` to be present.
- **Shared keyword source**: `BYPASS_MARKERS`, `SCOPE_MARKERS`, and `USER_CLAIM_MARKERS` in `intent.py` are now the single source of truth. `constraints.py`, `gui.py`, and `interactive_sandbox.py` import from there — no more desynchronized keyword lists.
- **`IntentDecomposer._intent_codes`**: Removed "做" (too generic, matches almost any Chinese sentence). Removed bare "agent" from `architecture_review` triggers (replaced with "母 agent", "子 agent", "agent 架构").

### UI/UX Overhaul

- **Chat stream interface**: First screen is now a ChatGPT-style chat flow, not a workbench form. Enter sends (Shift+Enter for newline). Task results appear as cards in the chat stream with "View details" buttons.
- **Conversation persistence**: All conversations saved to `localStorage`. Sidebar shows history list with search. Auto-titled from first user message.
- **Visual style upgrade**: High-contrast color system with brand accent gradient (orange→amber→gold). Chat bubble animations. Typing indicator. Welcome screen with gradient logo.
- **Task scope card**: File scope, acceptance anchors, workspace file browsing, paste-to-scope, drag-and-drop filename resolution, and per-conversation autosave now sit beside the chat composer so each request can carry explicit execution boundaries without a large form.
- **Settings page redesign**: Three section cards (Connection, Default File Scope, Safety Rules). "Test connection" button. Default scope presets remain available for repeat workflows.
- **Inspector toggle**: Right panel hidden by default. Toggle button in topbar (👁/🔍). Inspector now surfaces task context, permission boundary, and memory state; visibility is persisted to localStorage.
- **Progressive disclosure**: Composer status stack hidden until first task submission. Results use collapsible `<details>` for workflow timeline and audit details.
- **Violation explanations**: Chat stream now shows specific fix suggestions for each violation type (10 types, bilingual).
- **Memory panel**: Inspector shows curated memories with confidence percentages and delete buttons. Labeled "untrusted".

### LLM Integration Improvements

- **`tga_messages` prompt rewrite**: 7 explicit rules ensuring `proposed_outputs` contains actual deliverable content (not descriptions), `evidence` is file paths (not sentences), `test_commands` are real commands.
- **`repair_messages` prompt rewrite**: Specific fix instructions per violation type instead of generic "fix the violations".
- **`max_tokens`**: Increased from 800 → 4096 to avoid truncated JSON.
- **`LiveSpecialist` timeout**: Increased from 20s → 60s for code generation tasks.
- **Empty content check**: `call_live_llm` now raises a descriptive error if the LLM returns empty content.
- **DeepSeek compatibility**: Test connection prompt includes "json" keyword (required by DeepSeek's `response_format: json_object`).

### Backend API

- `GET /api/memory` — Retrieve curated memories.
- `POST /api/memory` — Delete individual memory (`{action: "delete", id: "..."}`) or clear all (`{action: "clear"}`).
- `POST /api/test-connection` — Test LLM connectivity with provider + key + model.
- `POST /api/list-files` — List workspace files for scope picker (excludes .git, node_modules, etc.).

### Other

- `.gitignore` added (config.json, memory.json, __pycache__, build artifacts, temp test files).
- API key cleared from config.json (defaults to mock provider).
- License metadata remains aligned on Apache-2.0 across `LICENSE`, `pyproject.toml`, `CITATION.cff`, and README badges.

## Unreleased (Pre-platform)

- Added the Text Graphics Agent research prototype.
- Added mother-side intent decomposition and clean `TaskSpec` creation.
- Added disposable child-agent lifecycle records.
- Added finite constraint checks for evidence, authority, scope, anchors, tests, metadata leaks, and confidence bounds.
- Added specialist profiles for raw-text, memory, scope, role, and tool boundaries.
- Added task graph and checkpoint primitives.
- Added deterministic contamination benchmark.
- Added paper draft, market survey, multilingual README, and public launch packaging.
- Added DeepSeek live API benchmark harness and smoke-result documentation.
- Added Chinese documentation mirrors and Chinese review checklist.
