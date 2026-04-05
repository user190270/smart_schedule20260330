# Current State

## Read Policy

- Read `docs/working_contract.md`, `docs/current_state.md`, and `docs/task_board.md` first.
- Read `docs/api_contract.md` only if interface implications need clarification.
- Read `docs/decision_log.md` only if an older RAG tradeoff must be explained.

## Round Context (R25 - RAG Context Rechunking And Local Time Grounding)

- `mode`: `TERMINAL`
- `project_title`: `Smart Schedule MVP - RAG Context Rechunking And Local Time Grounding`
- `round_target`: `Repair RAG answer quality by replacing raw fixed-width chunking, grounding indexed temporal text in local user-facing time, and consolidating retrieved evidence before generation.`

## Execution Status

- `current_phase`: `P4`
- `current_step`: `P4-S2`
- `status`: `completed`

## Problem Snapshot

- RAG currently uses `_to_chunks(...)` to slice cleaned schedule source text by fixed-width characters, which can split one schedule into multiple semantically broken fragments.
- The current source text contains duplicated bilingual labels plus raw ISO timestamps, which inflates chunk counts and makes retrieval snippets noisy.
- Retrieved snippets are forwarded to answer generation largely as-is, so the model sees repeated partial fragments instead of clean schedule-level candidates.
- Time-oriented answers remain unstable because retrieved context can expose UTC-looking timestamps that do not match the local-time view shown elsewhere in the product.

## Plan

### P1 - Docs refresh and boundary lock
- `P1-S1`: Refresh active docs for R25 and document the chunking / local-time / schedule-level aggregation scope.

### P2 - RAG source-text and chunking repair
- `P2-S1`: Replace raw fixed-width chunk slicing with schedule-aware chunk construction that keeps a schedule's factual context coherent.
- `P2-S2`: Rebuild schedule source text around concise local-time-oriented date/time facts instead of duplicated raw UTC-heavy text.

### P3 - Answer-context consolidation
- `P3-S1`: Consolidate retrieved chunk hits into schedule-level candidates before generation.
- `P3-S2`: Tighten the answer-generation prompt so time comparisons are performed against supplied structured candidates.

### P4 - Verification
- `P4-S1`: Add and update targeted RAG tests for chunk counts, local-time grounding, and schedule-level answer payloads.
- `P4-S2`: Run targeted RAG tests, broad backend regression, frontend build verification, and docs consistency checks.

## Done When

- A normal rebuild of a small schedule set no longer explodes into many arbitrary fixed-width chunks.
- Indexed schedule text presents user-facing local date/time facts instead of raw UTC-looking temporal strings.
- Runtime answer payloads are grouped by schedule rather than repeated per-fragment snippet noise.
- RAG answers to `earliest`, `latest`, `what date`, and `what time` style questions become materially more stable in local verification.
- True streaming and lightweight multi-turn follow-ups remain intact.

## Verification Results

- `docker compose exec api pytest tests/test_rag_workflow.py -q` -> `12 passed`
- `docker compose exec api pytest tests/test_ai_langchain_integration.py -q` -> `7 passed`
- `docker compose exec api pytest tests -q` -> `58 passed`
- `docker compose exec frontend npm run build` -> passed
- `docs_consistency_check.py --docs-root docs` -> pending rerun after terminal docs update
