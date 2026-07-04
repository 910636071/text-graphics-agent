# Public Launch Checklist

Use this before splitting `text-graphics-agent/` into a standalone public
repository.

## Repository

- [x] Choose and commit a public license: Apache-2.0.
- [x] Add `.gitignore` and Python package metadata.
- [x] Confirm repository URL and update `README.md`, `README.zh-CN.md`, and
      `CITATION.cff`.
- [x] Publish from a clean release export/repository, not from the private parent
      repository history.
- [x] Add public contact and submission-preparation notes.
- [ ] Add a social preview image from the Figma pitch.
- [ ] Tag `v0.1.0-paper-artifact`.
- [ ] Archive a release on Zenodo and add the DOI to `CITATION.cff`.

## Verification

- [x] `python tests/text_graphics_agent_test.py`
- [x] `python -m text_graphics_agent.demo`
- [x] `python -m text_graphics_agent.benchmark`
- [x] Optional: `python -m text_graphics_agent.api_benchmark --max-scenarios 2`
- [ ] Confirm benchmark output matches the README.
- [ ] Optional: build `dist/TextGraphicsAgent/TextGraphicsAgent.exe` for demos.
- [x] Confirm no generated cache files are committed (`.gitignore` covers config.json, memory.json, __pycache__).

## Platform

- [x] `Pipeline` class extracts business logic from `gui.py` (558-line god-function → 16-line delegate).
- [x] `BaseSpecialist` standard interface + `LocalSimulationSpecialist` + `LiveSpecialist`.
- [x] `AgentRegistry` with capability-based routing.
- [x] `ToolContext` with scope-enforced file tools (read_file, glob, grep).
- [x] Curated memory (`memory.py`) — untrusted context, never affects constraints.
- [x] `AsyncGraphExecutor` — concurrent + fail-fast.
- [x] Chat stream UI (ChatGPT-style) with localStorage history + search.
- [x] Right-side task scope card with per-task files, acceptance anchors, and workspace file browser.
- [x] Settings page with section cards, test connection, default scope, and safety rules.
- [x] Inspector panel with task context and memory display.
- [x] Bilingual i18n (zh/en) for all new features.
- [x] DeepSeek end-to-end live LLM verification (snake game task, accepted).

## Claims

- [x] Do not claim AGI.
- [x] Do not claim all hallucinations are solved.
- [x] Do not claim all prompt injection is prevented.
- [x] Keep the benchmark described as deterministic and closed-protocol.
- [x] Keep comparison to LangGraph/CrewAI/OpenAI Agents SDK as protocol-layer
      positioning, not replacement rhetoric.

## Paper

- [ ] Add DOI for `constraint-checked-state-records`, if available.
- [ ] Export benchmark output to JSONL.
- [x] Add real model-backed baseline before making empirical claims (DeepSeek live API benchmark completed).
- [ ] Add screenshot/multimodal contamination cases.
- [ ] Add shared-memory contamination cases.
