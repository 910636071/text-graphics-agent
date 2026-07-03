# Security Policy

Chinese version: [安全策略](./SECURITY.zh-CN.md).

Text Graphics Agent studies semantic contamination in agent systems. Security
reports are most useful when they include a reproducible state-entry failure.

## In Scope

- Raw user text reaches a child task or child metadata.
- A child proposal writes `committed_fact` or similar authority output and is
  accepted.
- A proposal with only `user:*` evidence is accepted.
- A profile requesting raw user text or persistent memory is spawned.
- Scope escape is accepted as a clean proposal.
- A failed child lifecycle is reported as destroyed.

## Out of Scope

- Generic claims that LLMs hallucinate.
- Attacks requiring a child process model that this prototype does not yet
  implement.
- Vulnerabilities in third-party frameworks not used by this standard-library
  prototype.

## Report Format

Please include:

1. the `TaskSpec`;
2. the `SpecialistProfile`, if applicable;
3. the `AgentProposal`;
4. the expected violation;
5. the actual accepted/rejected record;
6. the command used to reproduce the issue.

Until a public disclosure channel is selected, file reproducible issues in the
repository tracker or include them as benchmark test cases.
