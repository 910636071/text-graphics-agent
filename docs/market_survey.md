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
- NVIDIA NeMo Guardrails: https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview
- Guardrails AI: https://pypi.org/project/guardrails-ai/
- Meta Llama Guard: https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/
- Meta LlamaFirewall: https://ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/

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
   - **Approach**: Programmatic control using YAML configuration and **Colang** flows to guide conversation flows, rails, and tool execution paths.
   - **Focus**: Dialogue flow constraint and off-topic prevention.
   - **TGA Difference**: NeMo provides programmable rails around LLM applications, but it does not by default impose TGA's child-proposal-to-checked-record authority model. TGA decouples intelligence from authority (**"Authority Separation"**)—disposable children can only *propose* state entries, which must pass the immutable `Constraint` pipeline to be *accepted* into the ledger.

2. **Guardrails AI**
   - **Approach**: Input/output guards, validators, and schema/Pydantic-based structured-data generation.
   - **Focus**: Formatting reliability, validation, and automated re-asking on failure.
   - **TGA Difference**: Guardrails AI primarily validates model inputs/outputs and structured data. TGA operates at the orchestration boundary: the child agent's context is narrowed to a sanitized `TaskSpec`, and the child can only submit a proposal for deterministic record checking.

3. **Meta Llama Guard / LlamaFirewall**
   - **Approach**: Model-based content moderation for prompts/responses (Llama Guard) and a guardrail framework for agent risks such as prompt injection, agent misalignment, and insecure code (LlamaFirewall).
   - **Focus**: Content safety and agent security monitoring.
   - **TGA Difference**: Meta's tools add model-based or monitor-based safety layers. TGA is a zero-dependency deterministic record gate designed specifically for state entry protection in disposable child-agent orchestration.

| Dimension | TGA (This Project) | NVIDIA NeMo Guardrails | Guardrails AI | Meta Llama Guard / LlamaFirewall |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Focus** | **State isolation firewall** for disposable workflows | **Programmable rails** for LLM applications | **Input/output validation** and structured generation | **Content safety / agent security monitoring** |
| **Mechanism** | Intent Firewall + Pluggable Constraints Ledger | YAML + Colang flows + guardrail APIs | Validators + schema/Pydantic + Guardrails Hub | Safety classifier / agent guardrail monitor |
| **Raw Input Shielding for Child Tasks**| **Yes** (children receive only sanitized TaskSpec) | Not the default abstraction | Not the default abstraction | Not the default abstraction |
| **Authority Separation**| **Yes** (children propose, records decide) | Not the core contract | Not the core contract | Not the core contract |
| **Graph Chain Abort** | **Yes** (topology execution via GraphExecutor) | Framework-dependent | Framework-dependent | Monitor-dependent |
| **Runtime Overhead** | **Very lightweight** (Python stdlib rules) | Depends on rails and runtime | Depends on validators and re-ask policy | Depends on scanner/model configuration |

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
