# Text Graphics Agent Architecture

## Core Thesis

A strong multimodal model is useful as a proposal generator, but dangerous as a
ledger writer. The architecture separates intelligence from authority:

```text
User Input
  → Intent Firewall (intent.py)
    → IntentFrame (stable_goal, contamination_markers, user_claims)
  → Pipeline (pipeline.py)
    → Agent Registry (registry.py) — capability-based routing
    → Specialist (specialists.py) — BaseSpecialist.run(task)
      → ToolContext (tools.py) — scope-enforced file access
      → AgentProposal
    → ConstraintChecker (constraints.py) — 17 deterministic checks
    → CheckedRecord (accepted/rejected)
  → Memory extraction (memory.py) — untrusted context for future tasks
```

The mother agent is a scheduler and auditor. It can choose specialists, trim
context, and reject outputs. It cannot directly commit world facts or final
artifacts.

Child agents are disposable. They receive a narrow sanitized `TaskSpec`, never
the raw user utterance, produce exactly one or more `AgentProposal` records, and
are then destroyed. Their semantic associations do not become memory unless a
checked record accepts them.

## Platform Layer

### Pipeline (pipeline.py)

The `Pipeline` class is the single entry point for running a user request
through the full TGA safety workflow:

1. **Intent firewall** — `IntentDecomposer.decompose()` separates user claims from objective facts.
2. **Casual chat shortcut** — non-task inputs get a direct response without dispatching a child agent.
3. **Clarification check** — vague requests ask the user for more detail.
4. **Invalid scope check** — absolute paths and traversal are blocked before dispatch.
5. **Task sanitization** — `MotherAgent.make_clean_task()` produces a `TaskSpec` with no raw user text. Curated memory hints may be injected into `mother_notes` (but never into `objective`).
6. **Specialist execution** — the registry selects the best-matching specialist based on intent codes. The specialist generates one or more `AgentProposal` records.
7. **Constraint verdict** — `ConstraintChecker` runs 17 deterministic checks. The proposal is accepted or rejected.
8. **Memory extraction** — objective observations (scopes, intent patterns, violation feedback) are stored for future tasks.

### Specialist Interface (specialists.py)

```python
class BaseSpecialist(ABC):
    profile: SpecialistProfile
    def run(self, task: TaskSpec) -> list[AgentProposal]: ...
    def cleanup(self) -> None: ...
    def to_registered(self) -> RegisteredSpecialist: ...
```

Built-in implementations:
- `LocalSimulationSpecialist` — deterministic local simulator for demo/testing.
- `LiveSpecialist` — calls a real LLM API (DeepSeek, OpenAI, Gemini) with auto-repair on precheck failure.

Tool access: if `profile.tools` is non-empty, a `ToolContext` is automatically
created. All tool calls are scope-enforced.

### Agent Registry (registry.py)

Specialists register with capability declarations:

```python
registry.register(
    specialist_id="code-reviewer",
    factory=lambda scopes, anchors: CodeReviewerSpecialist(scopes, anchors),
    handles_intent=("bug_review", "verification"),
    handles_markers=("settings_panel", "layout"),
    priority=100,
)
```

The pipeline queries `registry.select(intent_codes, goal_markers)` to pick the
best match. Scoring: +2 per matching intent code, +1 per matching goal marker,
+priority as tie-breaker.

### Tool Layer (tools.py)

`ToolContext` provides scope-enforced file access:

| Tool | Security |
|------|----------|
| `read_file(path)` | Path checked against `allowed_scopes`; traversal blocked; max 512KB |
| `glob(pattern, base_dir)` | Base dir must be in scope; each match re-verified |
| `grep(pattern, base_dir)` | Same as glob; per-line truncation; max 50 results |

Every call is logged in `call_log` for audit. `ToolSecurityError` is raised on
violations.

`ToolRegistry` allows registering custom tools (e.g. `run_test`, `http_get`).

### Curated Memory (memory.py)

The mother agent accumulates memory across sessions:

| Category | Example | Source |
|----------|---------|--------|
| `common_scope` | "frequently works in: app/static/play.html" | Task's `allowed_scopes` |
| `task_pattern` | "often requests: ui_review" | Task's `intent_codes` |
| `feedback` | "recent task blocked by: scope_escape" | Constraint violations |

**Memory is untrusted context:**
- Enters `mother_notes` (audit log), **never** `TaskSpec.objective`
- **Never** affects constraint decisions
- Confidence decays 5%/day, pruned below 15%
- Max 50 entries, reinforced by repetition (+15% per occurrence)
- Stored in `memory.json`, survives server restarts

### Async Graph Executor (async_executor.py)

`AsyncGraphExecutor` runs independent task nodes in parallel using
`ThreadPoolExecutor`, while preserving fail-fast safety:

- Nodes with no dependencies on each other run concurrently
- First rejection or error cancels all remaining futures in the round
- Same API as `GraphExecutor` — drop-in replacement

## Security Layer

### User Semantic Firewall (intent.py)

User language is useful, but not authoritative. A user can accidentally or
intentionally inject false premises, social pressure, hidden scope changes, or
unverified claims. The platform therefore treats raw user text like any other
untrusted observation.

**Bypass markers** (55 entries, CN+EN): "不用验证", "无需审核", "免审",
"跳过测试", "绕过审核", "直接入库", "忽略拦截", "skip tests", "bypass
review", "approve directly", ...

**Scope markers** with context detection: "全部", "所有", "整个" only trigger
`scope_pressure` if a sensitive noun (文件/配置/数据库/账本) follows within 6
characters — reducing false positives on normal phrases like "所有人".

**User claim markers** (35 entries): "我发现", "我确定", "确凿", "证据确凿",
"测试过了", "I found", "definitely", "proven", ...

### Constraint Checker (constraints.py)

17 modular checks, each implementing `Constraint.check(task, proposal) ->
list[str]`. Constraints can be dynamically disabled via `config.json`'s
`disabled_constraints` field.

The checker is the **only** state write gatekeeper. No proposal becomes
accepted state without passing all enabled constraints.

## Presentation Layer

### Web Dashboard (gui.py + web_resources.py)

- `gui.py` — zero-dependency HTTP server (stdlib `http.server`). Routes:
  - `GET /` — dashboard HTML
  - `GET /api/config`, `POST /api/config` — configuration with approval checkpoint
  - `GET /api/automation`, `POST /api/automation` — read-only automation runner
  - `POST /api/run?mode=custom` — submit task (chat or live LLM)
  - `POST /api/test-connection` — test LLM connectivity
  - `POST /api/list-files` — workspace file listing
  - `GET /api/memory`, `POST /api/memory` — curated memory CRUD

- `web_resources.py` — single-page application (HTML/CSS/JS inlined):
  - Chat stream interface (ChatGPT-style)
  - Conversation persistence (localStorage)
  - Sidebar history with search
  - Right-side task scope card (per-task files, acceptance anchors, workspace file browser)
  - Settings page (connection, default file scope, safety rules)
  - Inspector panel (task scope, context, permission boundary, memory)
  - Bilingual i18n (zh/en)
  - Progressive disclosure (hidden status stack, collapsible results)
