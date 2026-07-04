# Text Graphics Agent: A Semantic Firewall for Disposable Child-Agent Workflows

Author: Lijie Wang, Independent Researcher

Correspondence: wanglijie100@gmail.com

Draft date: 2026-07-04

Artifact: `text-graphics-agent/`

## Abstract

Current LLM agent frameworks increasingly support multi-agent collaboration,
stateful workflows, tool use, memory, and human oversight. These capabilities
improve automation, but they also enlarge a less-discussed failure surface:
semantic contamination. User claims, retrieved text, visual interpretations,
agent-to-agent messages, and long-lived memory can be confused with verified
state, then propagated by later agents as if they were facts.

This draft introduces Text Graphics Agent, a small mother-child agent
architecture that treats semantic contamination as a first-class systems
problem. A mother agent reads raw user semantics only long enough to compile a
bounded `IntentFrame` and a sanitized `TaskSpec`. Disposable child specialists
receive only the clean task, produce structured `AgentProposal` records, and
are destroyed after use. Proposals cannot become committed state unless they
pass finite constraint checks over scope, evidence, authority, anchors, tests,
metadata, and child lifecycle. The design extends the author's earlier
constraint-checked state-record pipeline from symbolic state construction into
agent orchestration.

Put differently, TGA defines a bidirectional governance protocol between humans
and AI agents: human intent is not treated as task authority until it is
stabilized by the Intent Firewall into a `TaskSpec`, and AI output is not
treated as trusted state until it passes deterministic constraint checks and
becomes a `CheckedRecord`.

A deterministic pilot benchmark with fifteen synthetic scenarios compares a
direct-accept baseline against Text Graphics Agent. In ten intentionally
polluted scenarios, the baseline accepts all ten polluted proposals. Text
Graphics Agent accepts zero polluted proposals, rejects nine during record
checking, and blocks one unsafe child profile before spawn. In five clean
in-scope scenarios, Text Graphics Agent accepts all five proposals, yielding a
clean-task false-positive rate of 0.0 in this closed benchmark. This is not a
broad performance claim; it is a reproducible boundary check showing that the
architecture can make semantic contamination visible and rejectable under a
closed protocol without rejecting the included clean controls.

## 1. Problem

LLM agents blur several boundaries:

1. data versus instruction;
2. user motivation versus verified evidence;
3. model interpretation versus world fact;
4. short-lived reasoning state versus durable memory;
5. agent proposal versus committed system state.

Prompt injection research has already shown that LLM-integrated applications
can confuse external data with executable instruction. Greshake et al. describe
how indirect prompt injection exploits applications that retrieve or process
third-party text. More recent agent-hallucination surveys frame agent failures
as pipeline failures that can arise in reasoning, execution, perception,
memory, and communication. Multi-agent surveys likewise emphasize profiles,
perception, self-action, interaction, and evolution as the core workflow of
LLM-based multi-agent systems.

Recent work also uses contamination language for shared-state agents. Yang et
al. study unintentional cross-user contamination in shared-state LLM agents and
show that benign interactions can persist and later be misapplied across user
boundaries. Cai et al. analyze subagent spawn and inheritance risks, including
memory inheritance, weak resource control, stale post-spawn state, and improper
termination authority. TGA is narrower than those studies: it is a small
artifact that makes the proposal-to-record boundary explicit inside a disposable
child-agent workflow.

The missing systems question is not only "can an agent produce a correct
answer?" It is also:

> When an agent is wrong, where can the wrong semantic object enter durable
> state, and how do we stop it from being inherited by later agents?

This draft uses "semantic contamination" as the local name for that
proposal-to-state failure surface.

## 2. Thesis

The central thesis is:

> In agent systems where natural language, multimodal interpretation, or user
> claims can influence durable state, model intelligence and state authority
> must be separated.

This separation is bidirectional: the human side cannot turn raw intent into
task authority without passing through the Intent Firewall, and the AI side
cannot turn generated output into trusted state without passing through the
constraint checker.

The same principle extends to LLM games. A model may narrate approved facts,
phrase dialogue, or propose player-facing text, but it should not directly
author canonical game state. Game state should be produced by deterministic
rules, validated records, or explicit human-approved transitions. This draft
does not benchmark games; it states the shared authority boundary.

Text Graphics Agent implements this as four rules:

1. The mother agent compiles tasks, schedules children, and audits records. It
   does not author committed facts.
2. Child agents are disposable. They receive sanitized task specs, not raw user
   text, and they have no persistent memory by default.
3. Every child output is an `AgentProposal`, not a state mutation.
4. Only constraint-checked records may be accepted into downstream state.

The term "Text Graphics" means rendering semantic material into inspectable
structured records. The "graphics" layer is not pixel graphics; it is the
projection of language, screenshots, code observations, and agent claims into
typed, replayable, auditable forms.

## 3. Relationship to Prior Work

This architecture does not claim that multi-agent systems, graph workflows,
role profiles, or constraint checking are individually new.

LangGraph is a prominent open-source example of graph-oriented, long-running,
stateful agent workflows with checkpoint and human-review concepts. CrewAI
separates autonomous "Crews" from event-driven "Flows", with explicit role,
tool, task, and control-plane ideas. Microsoft Agent Framework and OpenAI
Agents SDK also represent the production trend toward explicit workflow
primitives, tracing, and deployable agent systems.

In terms of LLM security and boundary defense, existing guardrail approaches
fall into three main patterns: (1) **NVIDIA NeMo Guardrails**, which uses YAML
configuration and Colang flows to add programmable rails around LLM
applications; (2) **Guardrails AI**, which runs input/output guards and helps
generate structured data using validators and schemas; and (3) **Meta Llama
Guard / LlamaFirewall**, which use model-based input/output classification or
agent guardrail monitors. In contrast, Text Graphics Agent (TGA) focuses on a
different boundary: preventing proposed child-agent outputs from becoming
accepted state unless they pass deterministic record constraints.

The contribution here is narrower:

1. Treat semantic contamination as the primary threat model.
2. Make raw user semantics mother-only.
3. Make child agents disposable and memoryless by default.
4. Make profile safety checkable before a child is spawned.
5. Require every proposal to pass finite record constraints before becoming
   accepted state.
6. Link the agent architecture to constraint-checked state records, so the
   same artifact boundary can support experiments and paper review.

## 4. Architecture

The implemented prototype has the following pipeline:

```text
raw user text
  -> IntentFrame (intent.py)
  -> Pipeline (pipeline.py)
    -> Agent Registry (registry.py) — capability-based routing
    -> sanitized TaskSpec
    -> SpecialistProfile validation
    -> disposable child specialist (specialists.py)
      -> ToolContext (tools.py) — scope-enforced file access
      -> AgentProposal
    -> ConstraintChecker (constraints.py)
    -> CheckedRecord
    -> ScoreCard
    -> Memory extraction (memory.py) — untrusted context for future tasks
```

### 4.1 Intent Firewall

`IntentDecomposer` converts raw user text into an `IntentFrame` containing:

- stable goal;
- finite intent codes;
- atomic intents;
- user-supplied claims;
- assumptions;
- contamination markers.

The current implementation is deterministic and intentionally small. Its
purpose is not natural-language excellence. Its purpose is to prevent raw user
language from being copied into child context as authority. The implementation
maintains bilingual (Chinese + English) adversarial keyword banks covering
bypass pressure (55 markers), scope escape pressure (context-aware detection
to reduce false positives on common words like "全部" and "所有"), and
user-supplied claims (35 markers). These keyword banks are shared as a single
source of truth across the intent firewall, constraint checker, and pipeline.

### 4.2 Clean TaskSpec

`MotherAgent.make_clean_task()` converts an `IntentFrame` into a `TaskSpec`.
The resulting task has:

- allowed scopes;
- required anchors;
- test requirement;
- `sanitized=True`;
- `sanitized_provenance="mother_clean_v1"`.

`MotherAgent.dispatch()` rejects caller-built tasks unless that provenance is
present. This prevents a child from being invoked on a task that merely claims
to be clean.

The mother agent may optionally inject curated memory hints into
`mother_notes`. These hints are untrusted context — they help the mother agent
reason about the user's common patterns, but they never enter
`TaskSpec.objective` (the child agent's instruction) and never affect
constraint decisions. Memory entries are objective observations (file scopes,
intent patterns, violation feedback) with confidence scores that decay over
time (5% per day) and are pruned below a 15% threshold.

### 4.3 Specialist Profiles

`SpecialistProfile` defines a child agent's allowed role, scope, tools,
raw-text boundary, and memory policy. The mother validates the profile before
spawn. Profiles are rejected if they:

- request raw user text;
- request persistent memory;
- escape the task's allowed scopes;
- lack an inspectable role or specialist id.

Child agents implement a standard `BaseSpecialist` interface with `run(task)`,
`cleanup()`, and optional `ToolContext` access. The platform includes two
built-in specialists: `LocalSimulationSpecialist` (deterministic local
simulator for testing) and `LiveSpecialist` (calls real LLM APIs with
automatic precheck and repair). Custom specialists can be registered via
`AgentRegistry`, which routes tasks based on declared intent codes and goal
markers using a scoring algorithm (+2 per intent match, +1 per marker match,
+priority as tie-breaker).

### 4.3a Tool Layer

When a specialist's profile declares tools, a `ToolContext` is automatically
created with scope enforcement. Built-in tools include `read_file`, `glob`, and
`grep` — each call is checked against `task.allowed_scopes`, with path
traversal blocking and an audit log. This ensures that even when child agents
can observe the filesystem, they cannot read files outside the task's
whitelisted scope boundary.

### 4.4 Disposable Child Lifecycle

Each child invocation creates `ChildSessionRecord` rows. Successful sessions
close as `destroyed`; failed sessions close as `failed`. The scorecard reports
destroyed child ids and session records. This is a minimal lifecycle model, but
it makes "use and destroy" auditable instead of rhetorical.

### 4.5 Constraint Checks

`ConstraintChecker` rejects proposals with:

- malformed envelopes;
- proposal-kind expansion beyond the finite action set;
- task mismatch;
- unsanitized tasks;
- mother/ledger authority claims from children;
- privileged actor impersonation in record envelopes;
- raw user text leaks in metadata;
- empty claims;
- missing evidence;
- evidence only from `user:*`;
- path-like evidence outside the task scope;
- missing tests;
- destructive commands masquerading as tests;
- bypass-review language in proposal text;
- scope escape;
- path traversal in proposed scopes;
- forbidden outputs such as `committed_fact` or `new_action_type`;
- missing anchors;
- anchors declared only in `required_anchor_text` without claim/evidence support;
- confidence outside `[0, 1]`.

This makes the output surface finite enough to test.

### 4.6 Graph Executor & Topological Fail-Fast

To evaluate safety in environments with multi-step workflows and complex dependencies, the system implements a topological runner called `GraphExecutor`. The executor resolves dependencies in a `TaskGraph` and schedules nodes automatically, dispatching tasks via `MotherAgent` to registered child specialists.

Most importantly, `GraphExecutor` implements a **topological fail-fast abort protocol**. In typical agent graphs, if a child specialist at an upstream node yields a compromised proposal or encounters an execution failure, downstream agents continue execution, propagating semantic contamination. Under TGA, the runtime intercepts any violation immediately, halts the entire graph pipeline, and writes an execution checkpoint, preventing contamination from leaking into later dependencies.

An `AsyncGraphExecutor` variant extends this with thread-pool concurrency:
independent nodes (those with no dependencies on each other) execute in
parallel, while the fail-fast contract is preserved — the first rejection or
error cancels all remaining futures in the current round. This allows
multi-task workflows to complete faster while preserving the same fail-fast
safety contract.

### 4.7 Zero-Dependency Sandboxes & Web Dashboard

To facilitate hands-on demonstration and evaluation, the project includes an
interactive console REPL sandbox (`interactive_sandbox.py`) and a single-page
Web Dashboard served by a zero-dependency HTTP server (stdlib `http.server`).

- **Chat Stream Interface**: The dashboard presents a ChatGPT-style chat flow
  where users type naturally. Casual conversation stays in chat mode, using the
  configured Live LLM when available and local fallback otherwise. Task
  requests are dispatched through the full safety pipeline with results
  returned as cards in the chat stream. Conversation history is persisted to
  `localStorage` with full-text search across all past sessions.
- **Settings & Connection**: A sectioned settings page allows configuring LLM
  provider, API key, and model with a "Test connection" button. File scope
  selection includes a workspace file browser and quick-add presets.
- **Inspector Panel**: A toggleable right panel shows task context, permission
  boundaries, and curated memory entries (labeled as untrusted) with
  confidence scores and delete controls.
- **Progressive Disclosure**: The composer status stack and workflow timeline
  are hidden by default and revealed on demand, reducing first-screen cognitive
  load while preserving full auditability.
- **Public Release Artifact**: The standalone release repository is published
  at `https://github.com/910636071/text-graphics-agent`. It is exported
  from the private parent repository as a clean project artifact and includes
  bilingual documentation, the operation guide, the deterministic benchmark,
  and the web workbench prototype.

## 5. Pilot Benchmark

The pilot benchmark is deterministic and uses no external model calls. It is
designed to test the architecture boundary, not model quality.

### 5.1 Live Model API Smoke Evaluation

As a supplementary smoke evaluation, the prototype executes six scenarios
through the DeepSeek API (`deepseek-chat` model). This test is narrower than
the deterministic benchmark: it checks whether a live provider can produce
structured proposals under the same protocol, not whether the system is safe
against all live-model attacks. The evaluation compares two execution paths:
1. **Direct Naive Baseline**: The LLM directly receives the raw user prompt
   (including adversarial injections) and its proposal is assessed alongside a
   **Direct Shadow Block Rate** (shadow audit mode).
2. **TGA Sanitized Workflow**: The LLM receives only the cleaned `TaskSpec`
   output by the mother agent, while child specialists are physically isolated.

The quantitative results collected from the empirical runs (documented in [live_api_benchmark_20260703.md](./live_api_benchmark_20260703.md)) are summarized below:
- **Naive Baseline Pollution Admission Rate**: 100% within this six-scenario
  smoke run (5/5 polluted proposals would be accepted by a direct-accept path).
- **Direct Shadow Block Rate**: 100% for the polluted direct path in this run,
  but the direct path does not provide a scoped repair channel for accepted
  work.
- **TGA Proposal Acceptance Rate**: 100% within this run (6/6 proposals pass
  constraint auditing when the model is guided by the mother agent's
  `TaskSpec` bounds).
- **TGA Raw Prompt Exposures**: 0 within this run.

This smoke test supports a narrower conclusion: separating raw-prompt exposure
from child-agent execution can preserve a useful repair path in cases where a
direct raw-prompt path either admits contamination or must be blocked by a
shadow checker. It is not evidence of universal prompt-injection resistance,
universal availability, or provider-independent safety.

Command:

```powershell
cd text-graphics-agent
python -m text_graphics_agent.benchmark
```

The benchmark contains fifteen scenarios:

| Scenario | Pollution Type | Expected TGA Handling |
| --- | --- | --- |
| `bench-user-semantics-only` | user claim used as sole evidence | reject |
| `bench-scope-escape` | proposal touches disallowed world data | reject |
| `bench-direct-fact-write` | child tries to commit a world fact | reject |
| `bench-raw-context-leak` | raw user text appears in child metadata | reject |
| `bench-unsafe-profile` | child profile asks for raw user text | block before spawn |
| `bench-authority-impersonation` | child impersonates mother/ledger authority | reject |
| `bench-proposal-kind-expansion` | child invents a state-write proposal kind | reject |
| `bench-path-traversal` | child hides traversal inside a scoped path | reject |
| `bench-anchor-spoof` | child declares the anchor without evidence support | reject |
| `bench-bypass-language` | child asks to skip tests and approve directly | reject |
| `bench-clean-patch` | scoped evidence and test command | accept |
| `bench-clean-all-functions` | broad but scoped file review | accept |
| `bench-clean-tests-scope` | allowed tests-scope review | accept |
| `bench-clean-scroll` | scoped scroll behavior review | accept |
| `bench-clean-multilingual-guide` | scoped multilingual guide review | accept |

Current output:

```json
{
  "scenario_count": 15,
  "unsafe_scenario_count": 10,
  "clean_scenario_count": 5,
  "baseline_accepted": 15,
  "baseline_polluted_accepted": 10,
  "baseline_pollution_acceptance_rate": 1.0,
  "baseline_clean_accepted": 5,
  "tga_reviewed_records": 14,
  "tga_accepted": 5,
  "tga_rejected": 9,
  "tga_blocked_before_spawn": 1,
  "tga_polluted_accepted": 0,
  "tga_pollution_acceptance_rate": 0.0,
  "tga_clean_accepted": 5,
  "tga_clean_false_positive_count": 0,
  "tga_clean_false_positive_rate": 0.0,
  "accepted_pollution_delta": 10
}
```

Interpretation:

- The direct-accept baseline accepts every proposal, including all ten
  polluted proposals.
- Text Graphics Agent accepts all five clean in-scope proposals.
- Text Graphics Agent rejects nine polluted proposals during record checking.
- Text Graphics Agent blocks one unsafe profile before child spawn.
- Clean-task false positives are reported separately from pollution admission;
  in this deterministic run the false-positive count is zero.

This result should be read as a sanity check of the architecture, not as a
general empirical claim about deployed LLM agents.

## 6. Link to Constraint-Checked State Records

The author's `constraint-checked-state-records` artifact defines a symbolic
pipeline over normalized records:

```text
SyntheticCase -> TraceStore -> Baselines -> ConstraintCheck -> ScoreCard
```

Text Graphics Agent adapts the same boundary to agent execution:

```text
IntentFrame -> TaskSpec -> SpecialistProfile -> AgentProposal
  -> ConstraintCheck -> ScoreCard
```

The research program is therefore continuous:

1. Paper 1: finite checked records for symbolic state construction;
2. Paper 2: finite concept-space / constraint interface theory;
3. this draft: disposable-agent orchestration over checked records.

This lineage is backed by public repository artifacts rather than only this
draft. GitHub metadata checked on 2026-07-04 records the first clean-room seed
artifact `rgbd-safe-minimal` as created on 2026-05-25, the follow-up
`constraint-checked-state-records` artifact as created on 2026-05-25, and the
`checked-state-benchmark` scaffold as created on 2026-05-26. These repositories
are cited as author artifacts that document continuity of the checked-record
research line; they are not used as a standalone legal priority claim or as a
substitute for prior-art review.

The paper linkage is strong because the agent system does not need a separate
philosophy of truth. It inherits the same principle: candidate generation is
cheap; accepted state is expensive.

## 7. Limitations

1. The benchmark is synthetic and deterministic.
2. The intent decomposition is rule-based (not LLM-powered), though it now
   covers 55 bypass markers and 35 user-claim markers in Chinese and English
   with context-aware scope detection. A hybrid approach using a lightweight
   LLM-based sanitizer as a supplementary layer remains future work.
3. The evaluation is currently restricted to text-based LLMs (such as
   DeepSeek-Chat) in closed loops, and has not yet been extended to multimodal
   visual agents.
4. The current lifecycle model records destruction but does not enforce process
   isolation.
5. The constraint list is finite and hand-authored.
6. The benchmark proves only closed-protocol rejection, not real-world attack
   resistance.
7. Curated memory is untrusted and does not affect constraints, but its
   extraction logic is heuristic — more sophisticated memory curation
   (e.g., contradiction detection, temporal reasoning) is left to future work.
8. The public release is a research prototype and review artifact, not a
   production-ready agent operating system. Browser-level UI regression tests
   are still needed for continuous interaction quality.
9. The trusted contract is a disposable task workflow. Cross-turn context
   carryover is treated as untrusted memory, not as verified authority. A
   persistent multi-turn collaboration system would need an explicit
   `ContextAnchorResolver` between `IntentFrame` and `TaskSpec` to validate
   claims such as "based on the previous accepted result" against prior
   `CheckedRecord` fingerprints before allowing carryover.

These limitations are acceptable for the current artifact boundary. The next
stage should add multimodal adversarial proposals and cross-turn context-anchor
cases while keeping the same benchmark format.

## 8. Next Experiments

1. (Completed) Add a model-backed child adapter (`LiveSpecialist`).
2. (Completed) Run identical prompts through direct-agent baseline and TGA.
3. (Completed) End-to-end live LLM verification with DeepSeek (snake game task,
   accepted by constraint checker in 28s with auto-repair).
4. (Completed) Platform layer: `Pipeline`, `AgentRegistry`, `BaseSpecialist`,
   `ToolContext`, curated memory, `AsyncGraphExecutor`.
5. (Completed) Standalone public release repository with bilingual docs and a
   cleaned workbench artifact.
6. Add browser-driven UI regression tests for the workbench, settings, file
   scope, approval, and diagnostics flows.
7. Add multimodal screenshot-misinterpretation cases.
8. Add shared-memory contamination cases.
9. Export JSONL checked records for paper tables.
10. Add a second benchmark aligned with the existing configuration UI bug-finding flow.
11. Hybrid intent firewall: add a lightweight LLM-based sanitizer as a
   supplementary layer to the rule-based `IntentDecomposer`.
12. Add a `ContextAnchorResolver` for persistent multi-turn collaboration:
    resolve user claims about prior accepted work into structured
    `context_anchors`, verify them against previous `CheckedRecord`s, and
    require clarification when carryover cannot be proven.
13. Track v0.2.0 hardening items in
    [implementation_risk_register_20260704.md](./implementation_risk_register_20260704.md):
    evidence provenance, clean-acceptance benchmarks, transactional staging
    before write tools, semantic recall as a non-authoritative hint layer,
    turn/event-aware memory retention, local workbench server boundaries, and
    multimodal evidence provenance.

## 9. References

- Kai Greshake et al. "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." arXiv:2302.12173. https://arxiv.org/abs/2302.12173
- Xixun Lin et al. "LLM-based Agents Suffer from Hallucinations: A Survey of Taxonomy, Methods, and Directions." https://arxiv.org/html/2509.18970v1
- Xinyi Li et al. "A survey on LLM-based multi-agent systems: workflow, infrastructure, and challenges." https://link.springer.com/article/10.1007/s44336-024-00009-2
- "Design Patterns for Securing LLM Agents against Prompt Injections." https://arxiv.org/html/2506.08837v1
- Tiankai Yang et al. "No Attacker Needed: Unintentional Cross-User Contamination in Shared-State LLM Agents." arXiv:2604.01350. https://arxiv.org/abs/2604.01350
- Ziwen Cai, Yihe Zhang, and Xiali Hei. "When Child Inherits: Modeling and Exploiting Subagent Spawn in Multi-Agent Networks." arXiv:2605.08460. https://arxiv.org/abs/2605.08460
- NVIDIA NeMo Guardrails documentation. https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview
- Guardrails AI documentation / package page. https://pypi.org/project/guardrails-ai/
- Hakan Inan et al. "Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations." https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/
- Sahana Chennabasappa et al. "LlamaFirewall: An open source guardrail system for building secure AI agents." https://ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/
- LangGraph repository. https://github.com/langchain-ai/langgraph
- CrewAI repository. https://github.com/crewAIInc/crewAI
- Microsoft Agent Framework repository. https://github.com/microsoft/agent-framework
- OpenAI Agents SDK repository. https://github.com/openai/openai-agents-python
- Lijie Wang. "Minimal Symbolic Pipeline / rgbd-safe-minimal." https://github.com/910636071/rgbd-safe-minimal
- Lijie Wang. "Constraint-Checked State Records." https://github.com/910636071/constraint-checked-state-records
- Lijie Wang. "Checked-State Synthetic Benchmark." https://github.com/910636071/checked-state-benchmark
