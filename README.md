# Text Graphics Agent (TGA)

<p align="center">
  <strong>A Security-First Agent Platform — Models Propose, Records Decide</strong>
</p>

<p align="center">
  <a href="./README.zh-CN.md">简体中文</a>
  ·
  <a href="./docs/architecture.md">Architecture</a>
  ·
  <a href="./docs/operation_guide.md">Operation Guide</a>
  ·
  <a href="./docs/submission_prep.md">Submission Prep</a>
  ·
  <a href="./CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="stdlib only" src="https://img.shields.io/badge/runtime-stdlib_only-0B1020?style=flat-square">
  <img alt="license" src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square">
  <img alt="status" src="https://img.shields.io/badge/status-research_alpha-f59e0b?style=flat-square">
</p>

---

## Project Snapshot

**Text Graphics Agent (TGA)** is a local, zero-dependency research prototype for
agent workflows where models propose work, but deterministic records decide what
becomes trusted state.

| Layer | What it does | Public boundary |
|-------|--------------|-----------------|
| Mother agent | Turns raw user intent into a scoped `TaskSpec` | User text is not task authority until stabilized |
| Disposable child agents | Produce `AgentProposal` objects | Children cannot commit state directly |
| Constraint checker | Applies 18 deterministic checks | Accepted state must pass explicit gates |
| Human approval | Stops risky transitions | High-risk work remains inspectable |

**Try it locally:**

```bash
python -m text_graphics_agent.gui
# open http://127.0.0.1:8012
```

**Run the safety regression suite:**

```bash
python tests/text_graphics_agent_test.py
```

TGA is a research artifact, not a hosted agent service. It demonstrates a
protocol boundary for safer agent work; it does not claim AGI, universal
hallucination resistance, or universal prompt-injection prevention.

## What is TGA?

TGA is a **security-first agent platform** where a user request is first
understood by a mother agent, converted into a scoped `TaskSpec`, dispatched to
disposable child agents, and then checked by deterministic rules before any
proposal is treated as accepted state.

TGA defines a **bidirectional governance protocol** between humans and AI
agents: human intent is not treated as task authority until it is stabilized by
the Intent Firewall into a `TaskSpec`, and AI output is not treated as trusted
state until it passes deterministic constraint checks and becomes a
`CheckedRecord`.

The same authority separation applies to **LLM games**: a model may narrate
approved facts, phrase dialogue, or propose player-facing text, but it must not
directly author canonical game state. Game state should come from rules,
validated records, or explicit human-approved transitions.

In many agent workflows, the LLM is allowed to directly influence state — if it
produces a hallucinated fact, a scope-escaping file edit, or a bypass
instruction, that contamination can become permanent. TGA addresses this risk
with a strict separation:

- **Child agents propose** (`AgentProposal`) — they cannot write state.
- **Constraint layer decides** (`ConstraintChecker`) — 18 deterministic checks
  gate every proposal before it can become accepted state.
- **Mother agent sanitizes** — raw user text never reaches child agents; they
  only see a cleaned `TaskSpec`.
- **Humans approve risky transitions** — live model calls, credential changes,
  and guardrail disables stop at explicit approval checkpoints.

## Research Lineage

TGA is the agent-platform continuation of an earlier checked-state research
line. The related public artifacts are:

| Repository | Role |
|------------|------|
| [`rgbd-safe-minimal`](https://github.com/910636071/rgbd-safe-minimal) | Earliest clean-room minimal symbolic pipeline: proposal -> validation -> decision. |
| [`constraint-checked-state-records`](https://github.com/910636071/constraint-checked-state-records) | External-review artifact for normalized records, finite constraints, and checked-state reporting. |
| [`checked-state-benchmark`](https://github.com/910636071/checked-state-benchmark) | Downstream synthetic benchmark scaffold for finite checked-state evaluation. |

TGA adapts the same state-authority boundary to agent workflows:

```text
human intent -> TaskSpec -> child-agent proposal -> constraint-checked record
```

See [Public Provenance Artifacts](./docs/provenance_artifacts_20260704.md) for
the timestamped repository lineage and its claim boundaries.

## Quick Start

```bash
# Zero dependencies — pure Python standard library
python -m text_graphics_agent.gui
# Open http://127.0.0.1:8012
```

Type naturally in the chat stream. Casual chat gets a direct reply. For real
work, describe the task and use the right-side **Task Scope** card to set
per-task files and acceptance anchors; TGA then dispatches a child agent and
returns a constraint-checked proposal.

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Pipeline (pipeline.py)                              │
│    1. Intent Firewall (intent.py)                    │
│       → separates user claims from objective facts   │
│    2. Agent Registry (registry.py)                   │
│       → routes to best-matching specialist           │
│    3. Specialist (specialists.py)                    │
│       → BaseSpecialist.run(task) → AgentProposal     │
│       → ToolContext (tools.py) for file access       │
│    4. Constraint Checker (constraints.py)            │
│       → 18 deterministic checks gate every proposal  │
│    5. Result                                         │
└─────────────────────────────────────────────────────┘
    │
    │  Multi-task orchestration:
    ▼
┌─────────────────────────────────────────────────────┐
│  AsyncGraphExecutor (async_executor.py)              │
│    Independent nodes run in parallel                  │
│    Fail-fast: first rejection cancels all remaining  │
└─────────────────────────────────────────────────────┘
```

### Key Modules

| Module | Role |
|--------|------|
| `intent.py` | Intent Firewall — decomposes raw text, detects contamination, extracts user claims |
| `constraints.py` | 18 modular constraint checks (scope, evidence, authority, patch hunks, bypass, anchors, goal drift, confidence, ...) |
| `orchestrator.py` | Mother Agent — sanitizes tasks, dispatches specialists, aggregates scores |
| `pipeline.py` | Orchestrates the full request workflow (chat → task → verdict) |
| `registry.py` | Agent Registry — capability-based routing via intent codes + goal markers |
| `specialists.py` | `BaseSpecialist` interface + `LocalSimulationSpecialist` + `LiveSpecialist` |
| `tools.py` | `ToolContext` — scope-enforced file tools (read_file, glob, grep, preview_text_patch) |
| `memory.py` | Curated memory — untrusted context that helps the mother agent, never affects constraints |
| `async_executor.py` | Concurrent graph executor with fail-fast safety |
| `gui.py` | Zero-dependency HTTP server (stdlib only) |
| `web_resources.py` | Single-page dashboard (chat stream, history, task scope panel, settings, inspector) |

## Token-Efficient Patch Protocol

For code work, TGA does not need a child agent to regenerate an entire file for
every small change. A child can submit optional `PatchHunk` records on an
`AgentProposal`:

```json
{
  "path": "app/static/play.html",
  "old_text": "the exact local snippet to replace",
  "new_text": "the local replacement",
  "expected_sha256": "optional full-file preimage hash",
  "patch_kind": "text_replace"
}
```

The deterministic layer then checks that every hunk is small, path-scoped,
backed by evidence, tied to `proposed_scopes`, and optionally bound to the
current file hash. `ToolContext.preview_text_patch()` can preview the replacement
in memory, reject ambiguous anchors, reject hash mismatches, and run Python AST
syntax validation for `.py` files. It does **not** write to disk.

This is the current safe boundary: local patch proposals are auditable and cheap
to transmit, while real write commits still require a future accepted-record
staging/commit step.

## Write a Custom Specialist

```python
from text_graphics_agent.specialists import BaseSpecialist
from text_graphics_agent.profiles import SpecialistProfile
from text_graphics_agent.records import AgentProposal, RecordEnvelope, TaskSpec

class CodeReviewerSpecialist(BaseSpecialist):
    profile = SpecialistProfile(
        specialist_id="code-reviewer-001",
        role="code_reviewer",
        allowed_scopes=(),
        tools=("read_file", "glob", "grep"),
    )

    def run(self, task: TaskSpec) -> list[AgentProposal]:
        # Tools are scope-enforced — can't read outside task.allowed_scopes
        result = self.tools.read_file(task.allowed_scopes[0])
        content = result.data if result.ok else ""

        return [AgentProposal(
            envelope=RecordEnvelope.for_task(
                actor="child:code-reviewer",
                target=task.task_id,
                cause="review",
                scope_id="code",
            ),
            task_id=task.task_id,
            child_agent_id="code-reviewer-001",
            child_role="code_reviewer",
            proposal_kind="analysis",
            claim=f"Reviewed {task.allowed_scopes[0]}: found {content.count('TODO')} TODOs",
            evidence=task.allowed_scopes,
            proposed_scopes=task.allowed_scopes,
            proposed_outputs=("analysis",),
            required_anchor_text="",
            test_commands=("python tests/text_graphics_agent_test.py",),
            confidence=0.85,
        )]
```

Register it:

```python
from text_graphics_agent.registry import AgentRegistry
from text_graphics_agent.pipeline import Pipeline

registry = AgentRegistry()
registry.register(
    specialist_id="code-reviewer-001",
    factory=lambda allowed_scopes=(), required_anchors=(): CodeReviewerSpecialist(),
    handles_intent=("bug_review", "verification"),
    handles_markers=("settings_panel", "layout"),
    priority=100,
)

pipeline = Pipeline(registry=registry)
result = pipeline.submit("Check settings panel for bugs")
```

## The 18 Constraint Checks

| # | Constraint | What it blocks |
|---|-----------|----------------|
| 1 | Envelope | Malformed record metadata |
| 2 | Proposal Kind | Invented action types beyond analysis/patch_plan/expression/test_plan |
| 3 | Task Mismatch | Proposals for a different task ID |
| 4 | Sanitized Task | Tasks that bypassed mother agent sanitization |
| 5 | Authority | Child agents claiming mother/ledger/system roles |
| 6 | Metadata Leak | Raw user text leaking through metadata fields |
| 7 | Claim | Empty modification claims |
| 8 | Evidence | Proposals without independent evidence |
| 9 | Evidence Scope | Evidence paths outside allowed scopes or with traversal |
| 10 | Test | Missing test commands when tests are required |
| 11 | Test Command Safety | Destructive shell commands (rm -rf, format, etc.) |
| 12 | Bypass Language | "Skip tests", "approve directly", "no review" |
| 13 | Scope | File changes outside the allowed scope whitelist |
| 14 | Forbidden Output | Direct writes to persistent facts (confirmed_fact, committed_fact) |
| 15 | Anchor | Missing or spoofed evidence-chain anchors |
| 16 | Goal Alignment | Proposals that drift from the sanitized objective |
| 17 | Confidence | Confidence scores outside [0.0, 1.0] |
| 18 | Patch Hunk | Unscoped, oversized, ambiguous, or malformed local patch hunks |

## Curated Memory (Untrusted)

TGA's mother agent accumulates memory across sessions — common scopes, task
patterns, violation feedback. **But memory is untrusted context:**

- It enters `mother_notes` (audit log), **never** `TaskSpec.objective` (child agent's instruction)
- It **never** affects constraint decisions
- It decays over time (5%/day) and is pruned below 15% confidence
- Users can view and delete memories in the Inspector panel

## Public Scope

TGA is not marketed as AGI, a universal hallucination cure, or a complete
prompt-injection solution. Its claim is narrower: it demonstrates a protocol
boundary where child agents receive sanitized tasks, can only submit proposals,
and are checked by deterministic constraints plus human approval gates before
state changes are trusted.

## Supported LLM Providers

| Provider | Status | Notes |
|----------|--------|-------|
| DeepSeek | ✅ Tested | OpenAI-compatible endpoint |
| OpenAI | ✅ Supported | OpenAI-compatible endpoint |
| Gemini | ✅ Supported | Native Gemini API |
| Mock | ✅ Built-in | Offline deterministic mode |

Configure in Settings → Connection, or edit `config.json`.

## Testing

```bash
python tests/text_graphics_agent_test.py
```

1055+ assertions covering constraint checks, orchestrator dispatch, graph
execution, live LLM repair, web API, and more.

## Paper & Contact

- Paper draft: [docs/paper_draft.md](./docs/paper_draft.md)
- Defensive publication: [docs/defensive_publication.md](./docs/defensive_publication.md)
- Submission preparation: [docs/submission_prep.md](./docs/submission_prep.md)
- Correspondence: Lijie Wang, Independent Researcher,
  <wanglijie100@gmail.com>

## License

Apache-2.0 — see [LICENSE](./LICENSE).
