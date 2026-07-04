# Implementation Risk Register for v0.2.0, 2026-07-04

Chinese mirror: [v0.2.0 实现风险登记](./implementation_risk_register_20260704.zh-CN.md).

This register absorbs implementation-level review feedback after the public
`v0.1.0` review artifact. It does not change the `v0.1.0` release tag. It
records what must not be forgotten before claiming a stronger `v0.2.0`
implementation boundary.

## Priority Order

| Priority | Risk | Current v0.1.0 fact | v0.2.0 action |
| --- | --- | --- | --- |
| P1 | Evidence provenance gap | Evidence is mostly path strings checked for scope and traversal. The checker does not yet prove that a claim is derived from the cited file content. | Add evidence provenance records: `path`, `sha256`, optional `snippet_hash`, and `tool_call_id`. Require proposals to cite provenance for file-derived evidence. |
| P1 | Clean-request false positives | The benchmark is stronger on pollution rejection than on clean acceptance. `bench-clean-patch` is only one positive case. | Add a clean acceptance suite for legal broad requests inside explicit scope, such as "all functions in this file" or "whole allowed module". Report false-positive rate separately from pollution rejection. |
| P1 | Write-tool transaction boundary | Built-in `ToolContext` is read-only (`read_file`, `glob`, `grep`). The half-commit risk is not active in v0.1.0, but it becomes critical once write tools exist. | Before adding `write_file`, `run_command`, or patch tools, introduce a staging area. Writes must commit only after `CheckedRecord.accepted == true`; rejected or cancelled runs must discard staged effects. |
| P2 | Intent firewall recall gap | The first pass is deterministic marker/rule based. This is deliberate, but metaphorical bypass language may not be recalled. | Add optional semantic recall as a non-authoritative hint layer. Embedding or classifier output may raise suspicion or ask for clarification, but must not bypass deterministic constraints. |
| P2 | Memory decay semantics | Curated memory is untrusted and does not affect constraints. Calendar decay is acceptable for weak hints, not for future security policy. | If memory is ever used for safety routing, add turn/event-aware retention and separate safety feedback retention from ordinary preference decay. |
| P2 | Local workbench server boundary | The GUI uses a standard-library local server with `ThreadingMixIn`, not CGI and not a production web stack. | Keep it documented as a local research workbench. If live model calls become common in demos, add request timeouts, cancellation, or a small job queue before presenting it as robust UI infrastructure. |
| P3 | Multimodal evidence expansion | Current constraints are text/path oriented. Future screenshot/OCR cases could carry prompt text or hidden data through image-derived evidence. | Before adding multimodal evidence, extend provenance checks to image paths, OCR text, and derived feature records. Base64 image payloads should not become unchecked evidence. |

## Non-Goals for v0.1.0

- Do not claim transactional write-tool safety; v0.1.0 has no built-in write
  tools.
- Do not claim semantic recall or embedding-based intent detection.
- Do not claim production web-server hardening.
- Do not claim multimodal evidence safety.

## Suggested v0.2.0 Cut

The smallest credible v0.2.0 hardening pass should include:

1. Evidence provenance records and tests.
2. Clean acceptance benchmark cases with false-positive reporting.
3. A documented staging contract before any write-capable tool is added.

Everything else can remain future work until those three are in place.
