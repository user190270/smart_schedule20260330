# Progress Tracker (R17 - LangChain Integration and Async AI Service Hardening)

## Legend

- `[x]` Completed
- `[>]` Current
- `[ ]` Pending

## Round Rules

- This round is TERMINAL.
- Local implementation, local regression verification, and local frontend build are complete.
- GitHub synchronization and cloud deployment are explicitly deferred to a later round.

- [x] `P1` Shared LangChain runtime foundation
  - [x] `P1-S1` Add LangChain dependencies and a shared async AI runtime boundary for chat, structured parse output, embeddings, and streaming primitives.
  - [x] `P1-S2` Align AI router / service / provider seams to the new runtime entry points so Parse and RAG both consume the same async LangChain seam.
  - `done_when`: A reusable async LangChain runtime exists, dependency wiring is stable, and Parse / RAG can both consume the seam without holding request-scoped DB sessions during long upstream waits.
  - `verification_plan`: Import / compile the runtime, run backend regression, and keep `docs_consistency_check` green.

- [x] `P2` Parse LangChain refactor
  - [x] `P2-S1` Refactor Parse draft generation and session turn updates to a real LangChain chain with structured output and async provider calls while preserving follow-up, draft merge, and `ready_for_confirm` semantics.
  - [x] `P2-S2` Keep parse route and frontend contract compatibility while adding regression coverage that proves multi-turn updates and confirm-only persistence still hold.
  - `done_when`: Parse routes truly execute LangChain-backed orchestration without regressing the sessioned agent workflow.
  - `verification_plan`: `pytest server/tests/test_parse_contract.py -q` plus full backend regression.

- [x] `P3` RAG LangChain refactor
  - [x] `P3-S1` Preserve pgvector retrieval but refactor retrieval + answer orchestration to async LangChain components with a reusable context-assembly boundary.
  - [x] `P3-S2` Preserve `/api/rag/answer/stream` event names, SSE event semantics, and current frontend consumption behavior while ensuring chat-history writes happen through a short write session after AI output is available.
  - `done_when`: RAG retrieval and streamed answer generation use real LangChain orchestration without breaking the existing frontend / mobile SSE consumer or its current event handling assumptions.
  - `verification_plan`: `pytest server/tests/test_rag_workflow.py -q` plus full backend regression.

- [x] `P4` Async AI path hardening
  - [x] `P4-S1` Shorten DB session hold times in rebuild / retrieve / answer flows by splitting read -> external await -> write phases with explicit session boundaries.
  - [x] `P4-S2` Add timeout, error-wrapping, and logging hardening so AI failures are isolated from CRUD / sync / admin paths.
  - `done_when`: AI long waits no longer share the same long-held request DB session pattern, and error handling remains robust.
  - `verification_plan`: Code audit of AI route / service boundaries plus backend regression.

- [x] `P5` Verification and acceptance
  - [x] `P5-S1` Run backend regression for Parse, RAG, auth, CRUD, sync, sharing, admin, and schedule confirmation semantics.
  - [x] `P5-S2` Run the frontend production build locally without cloud integration.
  - `done_when`: Parse and RAG both run through real LangChain-backed core chains, backend regression passes, and the frontend build succeeds locally.
  - `verification_plan`: `pytest server/tests -q` and `docker compose exec frontend npm run build`.

- `current_phase`: `COMPLETED`
- `current_step`: `LOCAL BUILD VERIFIED`
