# Progress Tracker (R25 - RAG Context Rechunking And Local Time Grounding)

## Legend

- `[x]` Completed
- `[ ]` Pending

## Round Rules

- Keep this round scoped to RAG chunking, local-time temporal grounding, and schedule-level answer-context organization.
- Do not expand into Parse, sync, or frontend redesign work.
- Preserve true streaming and lightweight multi-turn follow-up behavior.
- Stay local only; no cloud deployment belongs in this round.

- [x] `P1` Docs refresh and planning lock
  - [x] `P1-S1` Refresh active round docs for R25 and document the exact boundaries.
  - `done_when`: working_contract, current_state, and task_board are refreshed for R25. Scope, constraints, and verification expectations are documented. Docs consistency check passes.
  - `verification_plan`: docs audit + `docs_consistency_check.py`.

- [x] `P2` RAG source-text and chunking repair
  - [x] `P2-S1` Replace raw fixed-width chunk slicing with schedule-aware chunk construction.
  - [x] `P2-S2` Rebuild indexed schedule text around concise local-time-oriented temporal facts.
  - `done_when`: one schedule is indexed as a coherent factual unit under normal rebuild settings, and temporal text is no longer dominated by raw UTC-style values or duplicated labels.
  - `verification_plan`: targeted RAG workflow tests.

- [x] `P3` Answer-context consolidation
  - [x] `P3-S1` Group retrieved evidence by schedule before generation.
  - [x] `P3-S2` Tighten answer-generation instructions for time-oriented questions.
  - `done_when`: runtime payloads carry schedule-level candidates instead of repeated fragment snippets, and multi-turn time questions operate on consolidated context.
  - `verification_plan`: targeted LangChain integration tests.

- [x] `P4` Verification
  - [x] `P4-S1` Run targeted RAG regression tests.
  - [x] `P4-S2` Run broader backend regression, frontend build verification, and final docs consistency checks.
  - `done_when`: targeted tests pass, broader backend tests pass, and round docs are moved to terminal state.
  - `verification_plan`: `docker compose exec api pytest ...` + `docker compose exec frontend npm run build` + docs check.

- `current_phase`: `P4`
- `current_step`: `P4-S2`
