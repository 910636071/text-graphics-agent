# Text Graphics Agent Packaging

This file packages the project for GitHub, Figma, paper abstracts, and short
technical demos. It is deliberately precise: this is not an AGI claim and not a
generic multi-agent platform.

## One-line Positioning

Text Graphics Agent is a semantic firewall for disposable child-agent workflows:
models propose, checked records decide.

## Short Pitch

Modern agent systems mix user claims, retrieved text, screenshots, model
interpretations, and memory inside the same context. If wrong semantics enter
durable state, later agents inherit them as facts.

Text Graphics Agent separates intelligence from authority. A mother agent sees
raw user language only long enough to compile a clean task. Disposable child
agents receive only sanitized task specs, produce structured proposals, and are
destroyed after use. A proposal can enter state only if it survives finite
checks over scope, evidence, authority, anchors, tests, metadata, and lifecycle.

## Taglines

- Models propose. Records decide.
- Do not make the smartest model the state writer.
- User semantics are motivation, not evidence.
- Candidate generation is cheap; accepted state is expensive.
- A state firewall for agent systems that need memory without contamination.

## README Hero

```md
# Text Graphics Agent

**A semantic firewall for disposable child-agent workflows.**

Text Graphics Agent treats semantic contamination as a systems problem. Raw
user requests are compiled by a mother agent into sanitized tasks. Child agents
receive only clean task specs, produce structured proposals, and are destroyed
after use. Only constraint-checked records may enter downstream state.

Current artifact:

- standard-library Python prototype;
- intent firewall;
- specialist profiles;
- task graph primitives;
- checked proposal records;
- deterministic contamination benchmark;
- paper draft.
```

## Figma Pitch Structure

Working design draft: https://www.figma.com/design/DqvS5sjyVDNQ9c5vkRcruY

The Figma file is a permission-controlled working asset. For a public release,
export a social preview image and link to that public asset unless the Figma
file itself is made public.

Frames:

1. `01 / Cover - Positioning`
   - Main message: Models propose. Records decide.
   - Visual: raw semantics -> mother agent -> checked records.

2. `02 / Architecture and Benchmark`
   - Pipeline: Raw user text -> IntentFrame -> Clean TaskSpec ->
     Profile check -> Disposable child -> Proposal -> Checked Record.
   - Evidence: 6 scenarios, 5 unsafe, baseline accepts 5 polluted proposals,
     TGA accepts 0 polluted proposals, 1 unsafe profile blocked before spawn.

3. `03 / Artifact and Roadmap`
   - Code artifact, paper draft, research link.
   - Next experiments: model-backed adapters, real prompts, multimodal
     screenshot cases, JSONL records for paper tables.

## Benchmark Claim

Safe phrasing:

> In a deterministic pilot benchmark with five intentionally polluted
> scenarios, a direct-accept baseline accepts all five polluted proposals. Text
> Graphics Agent accepts zero polluted proposals, rejects four during record
> checking, and blocks one unsafe child profile before spawn.

Avoid phrasing:

- "solves hallucination";
- "prevents all prompt injection";
- "is AGI architecture";
- "guarantees safety";
- "beats LangGraph/CrewAI/OpenAI Agents SDK."

## Comparison Positioning

Text Graphics Agent should not be framed as a replacement for LangGraph,
CrewAI, Microsoft Agent Framework, or OpenAI Agents SDK. It is a protocol layer
that can sit above or inside those runtimes:

- LangGraph gives stateful execution and graph control.
- CrewAI gives role/task/team modeling.
- OpenAI Agents SDK gives production agent primitives and tracing.
- Text Graphics Agent gives a semantic contamination boundary and checked state
  entry.

## Paper Abstract Compression

This paper introduces Text Graphics Agent, a mother-child agent architecture
that treats semantic contamination as a first-class systems risk. Raw user
language is compiled into sanitized task specs by a mother agent; disposable
child agents execute clean tasks and emit structured proposals; only
constraint-checked records may enter durable state. A deterministic pilot
benchmark shows that, under five polluted scenarios, a direct-accept baseline
admits all polluted proposals while Text Graphics Agent admits none and blocks
one unsafe child profile before spawn.

## Naming

Use:

- Text Graphics Agent
- TGA
- semantic firewall
- disposable child-agent workflow
- checked-record pipeline

Avoid:

- AI town agent;
- AGI mother brain;
- world model platform;
- anti-Gemini/anti-Claude framing.
