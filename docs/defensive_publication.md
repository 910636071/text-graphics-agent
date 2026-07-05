# Defensive Publication: Text Graphics Agent Protocol Boundary

Publication date: 2026-07-04

Author: Lijie Wang, Independent Researcher

Correspondence: wanglijie100@gmail.com

Artifact: `text-graphics-agent/`

Related documents:
- [Architecture](./architecture.md)
- [Paper Draft](./paper_draft.md)
- [Public Provenance Artifacts](./provenance_artifacts_20260704.md)
- [Citation Audit](./citation_audit_20260704.md)

## Status

This document is a public technical disclosure intended to make the Text
Graphics Agent (TGA) protocol boundary searchable and citable. It is written as
a defensive publication and prior-art aid, not as legal advice, not as a patent
application, and not as a claim that broad categories such as "AI safety",
"agent guardrails", "human-in-the-loop", or "LLM games" are owned by this
project.

The intended disclosure is the specific protocol family described below:
human intent is not treated as task authority until stabilized into a bounded
task record, and AI output is not treated as trusted state until it passes
deterministic record checks.

## Technical Field

The disclosed system concerns LLM agent orchestration, multi-agent workflows,
semantic-contamination control, proposal-to-record validation, human approval
gates, and state-authority separation for LLM-assisted systems, including LLM
agent platforms and LLM games.

## Problem Statement

LLM systems often blur five boundaries:

1. user intent versus executable task authority;
2. retrieved or remembered text versus verified evidence;
3. model interpretation versus durable fact;
4. child-agent output versus committed system state;
5. player-facing narration versus canonical game state in LLM games.

When these boundaries collapse, a model hallucination, prompt-injection string,
scope-escaping instruction, stale memory item, or unverified player-visible
statement can become persistent state. Later agents or game systems may then
inherit that state as if it were trusted.

## Core Disclosure

TGA discloses a bidirectional governance protocol:

```text
Human side:
Raw user input
  -> Intent Firewall
  -> IntentFrame
  -> sanitized TaskSpec
  -> task authority

AI side:
Disposable child agent output
  -> AgentProposal
  -> ConstraintChecker
  -> CheckedRecord
  -> trusted state
```

The system separates intelligence from authority:

- a mother agent may interpret, clarify, route, schedule, and audit;
- a child agent may perform bounded work and submit proposals;
- neither raw user text nor child-agent output is automatically trusted;
- deterministic constraints decide whether an output may become accepted state;
- high-risk transitions can require explicit human approval.

## Non-Limiting Terminology

The following names are examples. Equivalent implementations may rename these
components without changing the disclosed protocol boundary.

| TGA term | Equivalent names |
| --- | --- |
| Intent Firewall | intent stabilizer, task-authority gate, instruction firewall, semantic firewall |
| IntentFrame | stable intent record, bounded intent frame, request frame |
| TaskSpec | sanitized task, work spec, clean task record, scoped task contract |
| Mother Agent | scheduler, auditor, orchestrator, supervisor, routing agent |
| Disposable Child Agent | worker agent, specialist, ephemeral subagent, bounded executor |
| AgentProposal | proposed record, candidate patch, child output record, untrusted proposal |
| ConstraintChecker | record validator, deterministic checker, acceptance gate |
| CheckedRecord | accepted record, rejected record, validated state transition |
| ToolContext | scoped tool layer, capability boundary, file-scope wrapper |
| Curated Memory | untrusted memory hints, audit memory, advisory context |

## Protocol Steps

One implementation of the disclosed protocol performs the following steps:

1. Receive raw user input.
2. Decompose the input into a stable goal, user claims, contamination markers,
   required files, and acceptance anchors.
3. Reject, clarify, or hold the request when the input is ambiguous, scope-free,
   unsafe, or framed as a bypass instruction.
4. Convert the stable intent into a sanitized `TaskSpec` that does not expose
   raw user text to child agents.
5. Select a child-agent profile whose declared tools, scopes, and role match the
   sanitized task.
6. Deny child-agent spawn when the profile requests unsafe tools, persistent
   memory, authority to commit facts, or access outside the task scope.
7. Execute the child agent in a disposable lifecycle.
8. Restrict tool access through a scoped `ToolContext` or equivalent capability
   layer.
9. Require child output to be an `AgentProposal`, not a direct state mutation.
10. Run deterministic constraints over the proposal metadata, evidence, scope,
    authority, tests, anchors, and goal alignment.
11. Return accepted or rejected `CheckedRecord` results with visible rejection
    reasons.
12. Allow only accepted records, plus any required human approval, to influence
    downstream trusted state.
13. Store cross-session observations only as untrusted curated memory; memory
    may assist future mother-agent reasoning but must not directly become child
    instructions or constraint decisions.

## The 18 Deterministic Checks

The current TGA prototype implements 18 modular checks. The numbers are
descriptive, not limiting; equivalent implementations may combine or split
checks while preserving the same acceptance boundary.

| # | Check | Blocks |
| --- | --- | --- |
| 1 | Envelope | malformed record metadata |
| 2 | Proposal Kind | invented output kinds beyond the allowed action set |
| 3 | Task Mismatch | proposals for a different task ID |
| 4 | Sanitized Task | tasks that bypassed mother-agent sanitization |
| 5 | Authority | child agents claiming mother, ledger, system, or commit authority |
| 6 | Metadata Leak | raw user text leaking through metadata fields |
| 7 | Claim | empty or non-actionable modification claims |
| 8 | Evidence | proposals without independent evidence |
| 9 | Evidence Scope | evidence paths outside allowed scope or with traversal |
| 10 | Test | missing test commands when tests are required |
| 11 | Test Command Safety | destructive or unsafe shell commands |
| 12 | Bypass Language | "skip tests", "approve directly", "no review", or equivalent bypass text |
| 13 | Scope | proposed file changes outside the scope whitelist |
| 14 | Forbidden Output | direct writes to persistent facts such as `confirmed_fact` or `committed_fact` |
| 15 | Anchor | missing or spoofed evidence-chain anchors |
| 16 | Goal Alignment | proposals that drift from the sanitized objective |
| 17 | Confidence | confidence scores outside the accepted range |
| 18 | Patch Hunk | unscoped, oversized, ambiguous, or malformed local patch hunks |

## LLM Game State Boundary

The same authority split applies to LLM games.

In an LLM game, a model may narrate approved facts, phrase dialogue, summarize
state, or propose player-facing text. The model should not directly author
canonical game state. Canonical game state should be produced by deterministic
rules, validated records, explicit human-approved transitions, or an equivalent
state-authority mechanism.

One disclosed game-oriented mapping is:

```text
Player input
  -> intent/action stabilizer
  -> bounded game action
  -> rule engine or validated state transition
  -> canonical game state
  -> approved facts
  -> LLM narration/dialogue
  -> player-visible text
```

This document does not claim ownership over the broad idea of LLM games, AI
NPCs, game dialogue generation, or player-facing model narration. The disclosed
boundary is narrower: model output should be treated as expression or proposal,
not as canonical game-state authority, unless it passes an explicit validation
or approval mechanism.

## Non-Limiting Variations

The disclosed protocol covers, without limitation, implementations where:

- `TaskSpec`, `AgentProposal`, and `CheckedRecord` are renamed but keep the same
  authority transitions;
- the mother agent is deterministic, LLM-assisted, rules-assisted, or hybrid;
- child agents are local deterministic workers, live LLM calls, tool-running
  specialists, or multimodal interpreters;
- multiple child agents run sequentially, in parallel, or through a graph
  executor;
- constraints are implemented as functions, policy objects, schemas, type
  checks, formal validators, rule engines, or database constraints;
- human approval is required only for high-risk actions, or for every accepted
  state transition;
- evidence is text, code, file paths, screenshots, OCR, structured logs, or
  multimodal artifacts, provided provenance and scope are checked;
- memory is disabled, advisory only, decayed, manually curated, or replaced by
  a context-anchor resolver;
- the same boundary is applied to software agents, document agents, code
  review agents, local automation tools, game agents, or LLM games.

## Non-Claims And Boundaries

This disclosure does not claim:

- a general monopoly over AI safety, LLM guardrails, agent orchestration,
  graph workflows, human-in-the-loop review, or LLM games;
- a proof of universal prompt-injection resistance;
- a proof that all hallucinations are prevented;
- a production security guarantee;
- exclusive ownership of individual ideas such as schema validation, tool
  scoping, role profiles, or approval prompts.

The disclosed contribution is the specific combination of state-authority
separation, sanitized task authority, disposable child proposals, deterministic
record checks, visible rejection reasons, and trusted-state admission only after
validation.

## Defensive Publication Use

This document is intended to help future readers, reviewers, patent examiners,
or maintainers identify the TGA protocol family as publicly disclosed as of the
publication date above, subject to the repository history, release artifacts,
and public hosting timestamps.

For legal use, consult a qualified patent attorney. The project maintainer may
also publish this disclosure through additional timestamped channels such as a
GitHub release, Zenodo DOI, arXiv submission, or other public repository index.
