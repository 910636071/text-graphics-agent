# Agent Repository Survey

Survey date: 2026-07-03.

This note records what the prototype absorbs from current open-source agent
frameworks, and what it intentionally rejects for this project.

## Sources

- LangGraph: https://github.com/langchain-ai/langgraph
- CrewAI: https://github.com/crewAIInc/crewAI
- Microsoft Agent Framework: https://github.com/microsoft/agent-framework
- AutoGen legacy repository: https://github.com/microsoft/autogen
- OpenAI Agents SDK: https://github.com/openai/openai-agents-python

## Absorbed

1. State graph, not chat loop.
   LangGraph's useful idea here is explicit state and node progression. The
   prototype adds `TaskGraph`, `TaskNode`, and `ExecutionCheckpoint` instead of
   relying on a running transcript as state.

2. Role and task are configuration, not prose.
   CrewAI's practical contribution is explicit role/task/tool declarations.
   The prototype adds `SpecialistProfile` so a child agent's role, tool access,
   scope, memory policy, and raw-text boundary can be checked before spawn.

3. Workflows are production objects.
   Microsoft Agent Framework and OpenAI Agents SDK both point toward small
   workflow primitives that can be tested. The prototype keeps primitives
   intentionally small: intent frame, clean task, specialist profile, graph
   node, proposal, checked record, scorecard.

4. Human review belongs at checkpoints.
   The project already has a checked-record discipline. The prototype maps
   that to task graph checkpoints and scorecards rather than letting a mother
   model directly commit accepted output.

## Rejected

1. Persistent child memory.
   This project treats semantic contamination as the primary risk. Child
   profiles that request persistent memory are rejected before dispatch.

2. Raw user text in child context.
   The mother can read raw user language and compile intent codes. Children get
   only sanitized tasks. Profiles that allow raw user text are rejected.

3. Roleplay societies as authority.
   Role diversity is useful for adversarial review, but roleplay cannot write
   facts. Every child output still becomes an `AgentProposal` checked by finite
   constraints.

4. Framework lock-in.
   This folder stays standard-library only. The goal is to make the contracts
   portable before choosing any external runtime.

## Comparison with State-of-the-Art Guardrail Frameworks

To contextualize the academic and technical positioning of the Text Graphics Agent (TGA), we provide a comprehensive comparison with prominent LLM safety and guardrail frameworks in the current ecosystem:

1. **NVIDIA NeMo Guardrails**
   - **Approach**: Programmatic control using a specialized state-machine language called **Colang** to guide conversation flows and restrict tool usage paths.
   - **Focus**: Dialogue flow constraint and off-topic prevention.
   - **TGA Difference**: While NeMo restricts the dialogue flow, the LLM itself remains the direct author of persistent states. TGA decouples intelligence from authority entirely (**"Authority Separation"**)—disposable children can only *propose* state entries, which must pass the immutable `Constraint` pipeline to be *accepted* into the ledger.

2. **Guardrails AI**
   - **Approach**: Schema-based validation using Pydantic models to assert formatting constraints (e.g. JSON output validation) and run content validators (toxic speech, hallucinations, PII leakage).
   - **Focus**: Formatting reliability, validation, and automated re-asking on failure.
   - **TGA Difference**: Guardrails AI operates primarily as a content-level parser. TGA operates as a system-level firewall. For example, TGA physics-gates the child agent's context by sanitizing raw user inputs entirely out of the `TaskSpec`, cutting off direct prompt injection propagation.

3. **Meta Llama Guard**
   - **Approach**: Model-based content moderation using a dedicated fine-tuned classification LLM to label inputs and outputs as safe/unsafe based on a taxonomy of risk.
   - **Focus**: Natural language content moderation.
   - **TGA Difference**: Llama Guard introduces significant inference latency and depends on probabilistic model judgments. TGA is a zero-dependency, lightweight, deterministic rule-based validator designed specifically for state entry protection in multi-agent orchestration.

| Dimension | TGA (This Project) | NVIDIA NeMo Guardrails | Guardrails AI | Meta Llama Guard |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Focus** | **State isolation firewall** for disposable workflows | **Programmable state-machine** for dialogue flows | **Content/format validator** for structured output | **Content safety classifier** for moderation |
| **Mechanism** | Intent Firewall + Pluggable Constraints Ledger | Colang behavioral state files | Pydantic Schema + Validator Hub | Fine-tuned classifiers (model-based) |
| **Raw Input Shielding**| **Yes** (Children receive only Sanitized TaskSpec) | No (LLM is exposed directly to raw prompt) | No (LLM is exposed directly to raw prompt) | No (Text classified as-is) |
| **Authority Separation**| **Yes** (Children propose, records decide) | No (LLM remains the direct state writer) | No (LLM remains the direct state writer) | No (Classification-only) |
| **Graph Chain Abort** | **Yes** (Topology execution via GraphExecutor) | No | No | No |
| **Runtime Overhead** | **Very Lightweight** (Python stdlib rules) | Moderate (Colang runtime overhead) | Moderate (XML parsing and re-ask loops) | High (Requires extra LLM inference calls) |

## Implemented Platform Feature: Graph Executor (`GraphExecutor`)

Based on the research and adaptations above, we have successfully implemented the `GraphExecutor` runner (located in `graph.py`):
1. Loads and validates the topological dependencies of a `TaskGraph`;
2. Dynamically queries `ready_nodes()`;
3. Dispatches tasks only to registered specialists whose profiles satisfy task constraints using `MotherAgent`;
4. Collects and logs `ExecutionCheckpoint` rows (recording node status, accepted count, and rejected count);
5. Employs a fail-fast strategy: halts execution immediately if any proposal is rejected or a specialist raises an exception.

## Next Fit

1. Support process-level sandboxing for child agent execution (e.g. via `subprocess` or local containers) to prevent unauthorized read/write access to context and local memory.
2. Integrate multi-provider routing (e.g. DeepSeek + Gemini + OpenAI) and develop a more rigorous adversarial pollution dataset.
3. Perform deep integration testing between the TaskGraph orchestrator and the desktop pet's event log system.
