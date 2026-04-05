# API Contract (R25 Completed)

## Scope

- This round remains primarily backend-focused.
- Existing routes should remain stable unless a minimal default or metadata adjustment is necessary.
- No frontend request-shape churn is planned by default.

## RAG Boundary

- Existing RAG routes remain:
  - `POST /api/rag/retrieve`
  - `POST /api/rag/answer/stream`
  - `POST /api/rag/chunks/rebuild/{schedule_id}`
  - `POST /api/rag/chunks/rebuild-all`
- Existing SSE event contract remains:
  - `meta`
  - `token`
  - `done`

## Intended Semantic Changes

- Chunk construction is expected to become schedule-aware rather than raw fixed-width character slicing.
- Indexed content is expected to expose local-time-oriented date/time facts instead of raw UTC-heavy temporal text.
- Answer-generation payloads may become schedule-level grouped candidates rather than a flat list of arbitrary fragment snippets.

## Compatibility Guardrails

- Streaming remains true streaming.
- Lightweight multi-turn session behavior remains intact.
- No user-isolation change is allowed.
- Any request/response-shape change must be minimal, additive, and justified by implementation need rather than convenience.
