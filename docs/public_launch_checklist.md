# Public Launch Checklist

Use this before splitting `text-graphics-agent/` into a standalone public
repository.

## Repository

- [x] Choose and commit a public license: Apache-2.0.
- [x] Add `.gitignore` and Python package metadata.
- [ ] Confirm repository URL and update `README.md`, `README.zh-CN.md`, and
      `CITATION.cff`.
- [ ] Add a social preview image from the Figma pitch.
- [ ] Tag `v0.1.0-paper-artifact`.
- [ ] Archive a release on Zenodo and add the DOI to `CITATION.cff`.

## Verification

- [ ] `python tests/text_graphics_agent_test.py`
- [ ] `python -m text_graphics_agent.demo`
- [ ] `python -m text_graphics_agent.benchmark`
- [x] Optional: `python -m text_graphics_agent.api_benchmark --max-scenarios 2`
- [ ] Confirm benchmark output matches the README.
- [ ] Optional: build `dist/TextGraphicsAgent/TextGraphicsAgent.exe` for demos.
- [ ] Confirm no generated cache files are committed.

## Claims

- [ ] Do not claim AGI.
- [ ] Do not claim all hallucinations are solved.
- [ ] Do not claim all prompt injection is prevented.
- [ ] Keep the benchmark described as deterministic and closed-protocol.
- [ ] Keep comparison to LangGraph/CrewAI/OpenAI Agents SDK as protocol-layer
      positioning, not replacement rhetoric.

## Paper

- [ ] Add DOI for `constraint-checked-state-records`, if available.
- [ ] Export benchmark output to JSONL.
- [ ] Add real model-backed baseline before making empirical claims.
- [ ] Add screenshot/multimodal contamination cases.
- [ ] Add shared-memory contamination cases.
