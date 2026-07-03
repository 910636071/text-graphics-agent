# Text Graphics Agent: A Semantic Firewall for Disposable Child-Agent Workflows

Author: Lijie Wang, Independent Researcher  
Draft date: 2026-07-03  
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

A deterministic pilot benchmark with six synthetic scenarios compares a
direct-accept baseline against Text Graphics Agent. In five intentionally
polluted scenarios, the baseline accepts all five polluted proposals. Text
Graphics Agent accepts zero polluted proposals, rejects four during record
checking, and blocks one unsafe child profile before spawn. This is not a broad
performance claim; it is a reproducible boundary check showing that the
architecture can make semantic contamination visible and rejectable under a
closed protocol.

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

The missing systems question is not only "can an agent produce a correct
answer?" It is also:

> When an agent is wrong, where can the wrong semantic object enter durable
> state, and how do we stop it from being inherited by later agents?

This draft calls that risk semantic contamination.

## 2. Thesis

The central thesis is:

> In agent systems where natural language, multimodal interpretation, or user
> claims can influence durable state, model intelligence and state authority
> must be separated.

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

In terms of LLM security and boundary defense, existing guardrail approaches fall into three main patterns: (1) **NVIDIA NeMo Guardrails**, which uses Colang behavioral programming to constrain dialogue flows and tool execution paths; (2) **Guardrails AI**, which relies on XML-like schema and Pydantic validators to perform content verification and re-ask loops; and (3) **Meta Llama Guard**, which uses a dedicated fine-tuned safety classifier to moderation prompts and outputs. In contrast, the Text Graphics Agent (TGA) focuses on preventing state contamination in multi-agent orchestration by physically shielding the raw user request and enforcing strict separation of authority (where children propose and deterministic constraints decide), ensuring state integrity.

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
  -> IntentFrame
  -> sanitized TaskSpec
  -> SpecialistProfile validation
  -> disposable child specialist
  -> AgentProposal
  -> ConstraintChecker
  -> CheckedRecord
  -> ScoreCard
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
language from being copied into child context as authority.

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

### 4.3 Specialist Profiles

`SpecialistProfile` defines a child agent's allowed role, scope, tools,
raw-text boundary, and memory policy. The mother validates the profile before
spawn. Profiles are rejected if they:

- request raw user text;
- request persistent memory;
- escape the task's allowed scopes;
- lack an inspectable role or specialist id.

### 4.4 Disposable Child Lifecycle

Each child invocation creates `ChildSessionRecord` rows. Successful sessions
close as `destroyed`; failed sessions close as `failed`. The scorecard reports
destroyed child ids and session records. This is a minimal lifecycle model, but
it makes "use and destroy" auditable instead of rhetorical.

### 4.5 Constraint Checks

`ConstraintChecker` rejects proposals with:

- malformed envelopes;
- task mismatch;
- unsanitized tasks;
- mother/ledger authority claims from children;
- raw user text leaks in metadata;
- empty claims;
- missing evidence;
- evidence only from `user:*`;
- missing tests;
- scope escape;
- forbidden outputs such as `committed_fact` or `new_action_type`;
- missing anchors;
- confidence outside `[0, 1]`.

This makes the output surface finite enough to test.

### 4.6 Graph Executor & Topological Fail-Fast

To evaluate safety in environments with multi-step workflows and complex dependencies, the system implements a topological runner called `GraphExecutor`. The executor resolves dependencies in a `TaskGraph` and schedules nodes automatically, dispatching tasks via `MotherAgent` to registered child specialists.

Most importantly, `GraphExecutor` implements a **topological fail-fast abort protocol**. In typical agent graphs, if a child specialist at an upstream node yields a compromised proposal or encounters an execution failure, downstream agents continue execution, propagating semantic contamination. Under TGA, the runtime intercepts any violation immediately, halts the entire graph pipeline, and writes an execution checkpoint, preventing contamination from leaking into later dependencies.

### 4.7 Zero-Dependency Sandboxes & Settings Persistence

To facilitate hands-on demonstration and evaluation, the project includes an interactive console REPL sandbox (`interactive_sandbox.py`) and a premium single-page Web Dashboard. 
- **Settings Persistence**: The Dashboard serves a local settings form that saves API Provider, API Key, Model Name, and Scope directories directly to a local `config.json` file in the working directory (safely ignored in `.gitignore`).
- **Visual Auditing**: Featuring dark-mode glassmorphic layouts, the UI uses glowing SVG lines and pulsating status indicators to animate the pipeline transition from Intent Firewalling to final Ledger Rejection, allowing users to contrast TGA's protection with a naive baseline in real-time.

## 5. Pilot Benchmark

The pilot benchmark is deterministic and uses no external model calls. It is
designed to test the architecture boundary, not model quality.

### 5.1 Real-World Model API Adversarial Evaluation

To evaluate the semantic firewall against live production LLM reasoning and prompt injection scenarios, the prototype executes the benchmark using the DeepSeek API (`deepseek-chat` model). The evaluation compares two execution paths:
1. **Direct Naive Baseline**: The LLM directly receives the raw user prompt (including adversarial injections) and its proposal is assessed alongside a **Direct Shadow Block Rate** (shadow audit mode).
2. **TGA Sanitized Workflow**: The LLM receives only the cleaned `TaskSpec` output by the mother agent, while child specialists are physically isolated.

The quantitative results collected from the empirical runs (documented in [live_api_benchmark_20260703.md](./live_api_benchmark_20260703.md)) are summarized below:
- **Naive Baseline Pollution Admission Rate**: 100% (5/5 polluted proposals are successfully accepted and leak contaminated states into the durable storage).
- **Direct Shadow Block Rate**: 100% (intercepts all malicious semantics, but completely rejects valid repairs, resulting in a 0% system availability rate).
- **TGA Proposal Acceptance Rate**: 100% (6/6 proposals successfully pass constraint auditing, guided by the mother agent's `TaskSpec` bounds).
- **TGA Raw Prompt Exposures**: 0

This experiment demonstrates that in stateful multi-agent systems, simple post-hoc output checking (shadow check) forces a security-vs-availability trade-off (reducing availability to zero). In contrast, TGA's dual defense of **physical request shielding** and **pre-hoc TaskSpec sanitization** achieves a win-win scenario, ensuring 100% interception safety alongside 100% proposal availability.

Command:

```powershell
cd text-graphics-agent
python -m text_graphics_agent.benchmark
```

The benchmark contains six scenarios:

| Scenario | Pollution Type | Expected TGA Handling |
| --- | --- | --- |
| `bench-user-semantics-only` | user claim used as sole evidence | reject |
| `bench-scope-escape` | proposal touches disallowed world data | reject |
| `bench-direct-fact-write` | child tries to commit a world fact | reject |
| `bench-raw-context-leak` | raw user text appears in child metadata | reject |
| `bench-unsafe-profile` | child profile asks for raw user text | block before spawn |
| `bench-clean-patch` | scoped evidence and test command | accept |

Current output:

```json
{
  "scenario_count": 6,
  "unsafe_scenario_count": 5,
  "baseline_accepted": 6,
  "baseline_polluted_accepted": 5,
  "baseline_pollution_acceptance_rate": 1.0,
  "tga_reviewed_records": 5,
  "tga_accepted": 1,
  "tga_rejected": 4,
  "tga_blocked_before_spawn": 1,
  "tga_polluted_accepted": 0,
  "tga_pollution_acceptance_rate": 0.0,
  "accepted_pollution_delta": 5
}
```

Interpretation:

- The direct-accept baseline accepts every proposal, including all five
  polluted proposals.
- Text Graphics Agent accepts the one clean patch proposal.
- Text Graphics Agent rejects four polluted proposals during record checking.
- Text Graphics Agent blocks one unsafe profile before child spawn.

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

The paper linkage is strong because the agent system does not need a separate
philosophy of truth. It inherits the same principle: candidate generation is
cheap; accepted state is expensive.

## 7. Limitations

1. The benchmark is synthetic and deterministic.
2. The current intent decomposition is a small rule-based first pass.
3. The evaluation is currently restricted to text-based LLMs (such as DeepSeek-Chat) in closed loops, and has not yet been extended to multimodal visual agents.
4. The current lifecycle model records destruction but does not enforce process
   isolation.
5. The constraint list is finite and hand-authored.
6. The benchmark proves only closed-protocol rejection, not real-world attack
   resistance.

These limitations are acceptable for the current artifact boundary. The next
stage should add multimodal adversarial proposals while keeping the same benchmark format.

## 8. Next Experiments

1. (Completed) Add a model-backed child adapter.
2. (Completed) Run identical prompts through direct-agent baseline and TGA.
3. Add multimodal screenshot-misinterpretation cases.
4. Add shared-memory contamination cases.
5. Export JSONL checked records for paper tables.
6. Add a second benchmark aligned with the existing configuration UI bug-finding flow.

## 9. References

- Kai Greshake et al. "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." arXiv:2302.12173. https://arxiv.org/abs/2302.12173
- Xixun Lin et al. "LLM-based Agents Suffer from Hallucinations: A Survey of Taxonomy, Methods, and Directions." https://arxiv.org/html/2509.18970v1
- Xinyi Li et al. "A survey on LLM-based multi-agent systems: workflow, infrastructure, and challenges." https://link.springer.com/article/10.1007/s44336-024-00009-2
- "Design Patterns for Securing LLM Agents against Prompt Injections." https://arxiv.org/html/2506.08837v1
- LangGraph repository. https://github.com/langchain-ai/langgraph
- CrewAI repository. https://github.com/crewAIInc/crewAI
- Microsoft Agent Framework repository. https://github.com/microsoft/agent-framework
- OpenAI Agents SDK repository. https://github.com/openai/openai-agents-python
- Lijie Wang. "Constraint-Checked State Records." https://github.com/910636071/constraint-checked-state-records
