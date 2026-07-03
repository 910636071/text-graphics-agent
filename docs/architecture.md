# Text Graphics Agent Architecture

## Core Thesis

A strong multimodal model is useful as a proposal generator, but dangerous as a
ledger writer. The architecture separates intelligence from authority:

```text
MotherAgent
  -> IntentFrame(raw user semantics; mother side only)
  -> Clean TaskSpec(no raw user text)
  -> Disposable specialist agents
  -> AgentProposal records
  -> ConstraintChecker
  -> CheckedRecord ledger
  -> ScoreCard
```

The mother agent is a scheduler and auditor. It can choose specialists, trim
context, and reject outputs. It cannot directly commit world facts or final
artifacts.

Child agents are disposable. They receive a narrow sanitized `TaskSpec`, never
the raw user utterance, produce exactly one or more `AgentProposal` records, and
are then destroyed. Their semantic associations do not become memory unless a
checked record accepts them.

## Record Flow

The flow mirrors the checked-record pipeline:

```text
raw observation / task
  -> IntentFrame
  -> normalized TaskSpec
  -> child-agent proposal
  -> constraint checks
  -> accepted/rejected CheckedRecord
  -> aggregate ScoreCard
```

## User Semantic Firewall

User language is useful, but not authoritative. A user can accidentally or
intentionally inject false premises, social pressure, hidden scope changes, or
unverified claims. The platform therefore treats raw user text like any other
untrusted observation.

```text
raw user utterance
  -> IntentFrame(
       stable_goal,
       atomic_intents,
       user_supplied_claims,
       assumptions,
       contamination_markers
     )
  -> Clean TaskSpec
  -> Disposable child task
```

Rules:

1. A child agent may cite `user:*` evidence, but it cannot be the only evidence.
2. User-supplied claims remain claims until code, tests, tools, or records
   verify them.
3. If the raw request asks to bypass review, skip tests, write facts directly,
   or expand scope silently, the intent frame marks contamination and the mother
   agent must lower authority.
4. The mother agent may decompose intent, but it must not let decomposed intent
   become committed state.
5. Child agents never receive `raw_text`; they receive only stable objective,
   allowed scopes, anchors, and verification requirements.
6. Sanitization is not caller-declared. `MotherAgent.dispatch()` only accepts
   tasks with `sanitized=True` and `sanitized_provenance="mother_clean_v1"`,
   produced by `make_clean_task()`.

## Constraint Families

The proposal validation system is implemented as a polymorphic, pluggable pipeline. Each individual rule inherits from a base `Constraint` class. The framework loads 12 core firewall constraints by default (which can be customized at `ConstraintChecker` instantiation):

1. **Envelope constraints (`EnvelopeConstraint`)**
   Every record must carry actor, target, cause, result, visibility, source id,
   scene/scope, and timestamp.

2. **Scope constraints (`ScopeConstraint`)**
   A child agent may only touch paths or domains listed in the task. Scope
   escape is a hard rejection.

3. **Authority constraints (`AuthorityConstraint`)**
   Proposals cannot write committed world facts, mutate ledgers, invent action
   types, or bypass review.

4. **Anchor constraints (`AnchorConstraint`)**
   Expressions must preserve required anchors from the fact packet. A candidate
   that drops an anchor is rejected and falls back to template/default behavior.

5. **Evidence and test constraints (`EvidenceConstraint` & `TestConstraint`)**
   A proposal must cite evidence and, for implementation tasks, provide test
   commands or verification steps.

6. **User-semantics constraints (`ClaimConstraint` & `SanitizedTaskConstraint`)**
   A proposal is rejected if all evidence comes from `user:*` sources. User
   semantics can motivate a task; they cannot prove the task result.

7. **Lifecycle constraints**
   Every specialist invocation creates `ChildSessionRecord` rows. Successful
   sessions close as `destroyed`; failed sessions close as `failed`. The
   `ScoreCard` reports `child_sessions` and `destroyed_child_ids`.

## Dogfood Round 1

The first use of this architecture against itself found four real issues:

1. `TaskSpec.objective` could still copy raw user semantics.
2. `TaskSpec.sanitized` defaulted to trusted before the mother cleaned it.
3. Metadata leak detection only checked one top-level key.
4. Child lifecycle identity could collapse multiple child IDs into one session.

The current prototype fixes those by using intent codes, provenance-gated clean
tasks, recursive forbidden metadata-key scanning, and one lifecycle record per
child ID.

## Market Survey Absorption

The prototype borrows structure, not runtime dependency, from current agent
frameworks:

- LangGraph: explicit task graph, ready nodes, and the checkpoint-oriented, fail-fast execution logic in `GraphExecutor`.
- CrewAI: explicit specialist profiles instead of role text hidden in prompts.
- Microsoft Agent Framework / OpenAI Agents SDK: small workflow primitives that
  can be tested outside a chat transcript.

This maps to two local modules:

- `profiles.py`: mother-side validation for child role, scope, tool surface,
  raw-text access, and persistent-memory policy.
- `graph.py`: task nodes, dependencies, ready-node selection, checkpoint definitions, and the `GraphExecutor` runner which topologically drives execution and aborts immediately upon rejections or failures.

The prototype still rejects persistent child memory and raw user text in child
context, because semantic contamination is the threat model.

## Pilot Benchmark

`benchmark.py` compares a direct-accept baseline against the mother-child
pipeline over six deterministic contamination scenarios. The current run has
five unsafe scenarios and one clean scenario: baseline accepts all five polluted
proposals, while Text Graphics Agent accepts zero polluted proposals, rejects
four through `ConstraintChecker`, and blocks one unsafe profile before spawn.

The benchmark is a closed-protocol sanity check, not a broad deployment claim.
It is meant to become the reproducible evidence table for `docs/paper_draft.md`.

## Why "Text Graphics"

The "graphics" layer is the structured projection of text into state:

- facts become typed records;
- records become visible UI or logs;
- UI screenshots become metric observations;
- agent claims become checked records;
- scorecards become the rendered shape of platform health.

This lets a multimodal mother model use visual and semantic association without
letting those associations write authority state.

## Non-goals

- No free-text parsing into world facts.
- No child-agent persistent memory.
- No automatic rule creation.
- No secret or account access.
- No operational integration with the game runtime yet.
