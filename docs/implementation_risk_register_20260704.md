# Implementation Risk Register for v0.2.0, 2026-07-04

Chinese mirror: [v0.2.0 实现风险登记](./implementation_risk_register_20260704.zh-CN.md).

This register absorbs implementation-level review feedback after the public
`v0.1.0` review artifact. It does not change the `v0.1.0` release tag. It
records what must not be forgotten before claiming a stronger `v0.2.0`
implementation boundary.

## Priority Order

| Priority | Risk | Current v0.1.0 fact | v0.2.0 action |
| --- | --- | --- | --- |
| P1 | Evidence provenance gap | `v0.1.0` evidence is mostly path strings checked for scope and traversal. A local `v0.2.0` candidate now has opt-in `EvidenceProvenance`, `ToolContext.read_file()` sha256 provenance, and strict-task tests, but this is not yet a released default. | Keep the schema, migrate real proposal producers toward provenance-carrying evidence, and decide which v0.2.0 task classes require `requires_evidence_provenance=True`. |
| P1 | Clean-request false positives | `v0.1.0` had only one clean positive benchmark case. The local `v0.2.0` candidate now has five clean in-scope scenarios and reports clean false positives separately. | Keep the clean suite in the deterministic benchmark and expand it only when new constraints or task classes are added. |
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

## v0.2.0 Readiness Gates

The `v0.2.0` label should be treated as an implementation-hardening gate, not
as a production-readiness claim. A release can be called `v0.2.0` only if the
following artifacts exist and are checked into the repository:

| Gate | Required artifact | Pass condition | Claim unlocked |
| --- | --- | --- | --- |
| G1 | Evidence provenance schema and tests | File-derived proposal evidence includes `path`, `sha256`, `tool_call_id`, and optional snippet or range hashes; negative tests reject missing or mismatched provenance. | TGA can claim auditable file-derived evidence, not merely path-scoped evidence. |
| G2 | Clean acceptance benchmark | At least five clean in-scope tasks pass, including broad-but-scoped requests such as "all functions in this file" and "whole allowed module". False positives are reported separately from pollution rejection. | TGA can report a clean-task false-positive rate alongside rejection rate. |
| G3 | Write-tool staging contract | If write-capable tools exist, their effects are staged and discarded on rejection, cancellation, or failed approval. If no write tools exist, the contract is documented as a precondition before adding them. | TGA can discuss write-tool safety only within the documented staging boundary. |
| G4 | Context carryover boundary | Cross-turn claims such as "based on the previous result" remain untrusted unless a `ContextAnchorResolver` or equivalent verifier is implemented and tested. | TGA can keep v0.2.0 scoped to disposable tasks, or explicitly claim verified context anchors if implemented. |
| G5 | Workbench reliability boundary | Local server docs and tests cover timeout/cancellation behavior for live calls, or the UI remains labeled as a local research workbench. | TGA can avoid presenting the web client as production infrastructure. |

These gates deliberately leave semantic recall, multimodal evidence, and
production deployment hardening outside the minimum `v0.2.0` scope unless they
are implemented and tested in the same pass.

## Local v0.2.0 Progress

As of the local worktree after this register update, G1 and G2 have
implementation candidates:

- `EvidenceProvenance` records exist on `AgentProposal`.
- `TaskSpec.requires_evidence_provenance` enables strict provenance mode.
- `ToolContext.read_file()` produces `path`, full-file `sha256`,
  `tool_call_id`, and optional `snippet_hash` provenance.
- Model-supplied provenance parsing is strict: provenance entries must be JSON
  objects, and `path`, `sha256`, `tool_call_id`, and optional `snippet_hash`
  must be strings.
- `EvidenceConstraint` rejects missing, malformed, out-of-scope, or unreferenced
  provenance. `requires_evidence_provenance=False` does not require provenance,
  but any provenance supplied by a proposal is still validated.
- Tests cover accepted tool-derived provenance, truncated snippet provenance,
  parse failures, and negative cases for missing provenance, bad hashes, missing
  tool IDs, path traversal, empty paths, bad snippet hashes, scope escape,
  optional malformed provenance, and unreferenced provenance.
- The deterministic benchmark now has 15 scenarios: 10 intentionally polluted
  scenarios and 5 clean in-scope scenarios.
- The clean suite includes broad-but-scoped file review, allowed tests-scope
  review, scroll behavior review, and multilingual guide review.
- The current deterministic output reports `tga_polluted_accepted=0`,
  `tga_clean_accepted=5`, and `tga_clean_false_positive_rate=0.0`.

This is still a local 0.2.0 implementation candidate until committed, pushed,
and included in a new release tag.
