# API Contract (R17 Active)

## Scope

- This file is the active boundary for the AI service-layer refactor round.
- Existing local-first schedules, Push / Pull, sharing, auth, and admin flows remain in force.
- This round mainly changes internal orchestration and async behavior of AI routes while preserving user-facing contracts unless a minimal, explicitly documented enhancement is required.

## Parse Contract To Preserve

- `POST /api/parse/schedule-draft`
  - returns `draft`, `missing_fields`, `follow_up_questions`, `requires_human_review`, and `can_persist_directly`
- `POST /api/parse/schedule-draft/stream`
  - keeps SSE event flow with `draft`, optional `follow_up`, and terminal `done`
- `POST /api/parse/sessions`
- `POST /api/parse/sessions/{session_id}/messages`
- `PATCH /api/parse/sessions/{session_id}/draft`
  - keeps `parse_session_id`, `messages`, `draft`, `missing_fields`, `follow_up_questions`, `ready_for_confirm`, `next_action`, `tool_calls`, `latest_assistant_message`, and `draft_visible`

Mandatory Parse guarantees:

- Parse remains draft-first and does not persist schedules directly.
- AI parsed schedules still require explicit user confirmation before storage.
- Multi-turn clarification, draft updates, and `ready_for_confirm` semantics remain intact.
- Internal implementation may become async, but external payload shapes must remain compatible with the current frontend unless a minimal enhancement is explicitly planned.

## RAG Contract To Preserve

- `POST /api/rag/chunks/rebuild/{schedule_id}`
- `POST /api/rag/chunks/rebuild-all`
- `POST /api/rag/retrieve`
- `POST /api/rag/answer/stream`
  - keeps SSE event names `meta`, `token`, and `done`
  - keeps the current frontend / mobile consumer contract usable without a breaking rewrite

Mandatory RAG guarantees:

- Retrieval remains user-scoped.
- PostgreSQL + pgvector retrieval remains the underlying retrieval basis.
- Chat history still persists after a successful answer path.
- `/api/rag/answer/stream` must keep its existing SSE event semantics and remain consumable by the current frontend streaming client.
- Internal answer generation must move to real LangChain orchestration rather than a direct handwritten provider call.

## Async AI Boundary Contract

- Ordinary CRUD routes may remain synchronous in this round.
- AI routes and AI services may adopt a different internal execution style if that is what is required to avoid long external waits holding DB resources.
- Target AI path split:
  1. short DB read session for required state or retrieval inputs
  2. no DB session held while awaiting external model or embedding work
  3. short DB write session for durable state updates such as vector chunks or chat history
- AI routes must not keep dependency-injected long-lived request DB sessions alive while awaiting external model or embedding work; if needed, services should own short read / write sessions instead.
- Simply changing route signatures to `async def` is not sufficient; provider and service layers must participate in a real await chain.

## LangChain Integration Contract

- Required real usage target:
  - Parse chain: prompt + structured output / runnable flow for extraction and draft update
  - RAG answer chain: context assembly + prompt + model interaction through LangChain objects
- LangChain does not need to replace pgvector SQL retrieval.
- Embedding calls may use a LangChain embeddings wrapper or a shared async provider abstraction, but Parse and RAG both must execute a real core chain through LangChain by round close.

## Verification Contract

Required round-close acceptance:

1. Parse multi-turn clarification still works.
2. Parse draft confirmation remains the only path to local persistence for AI parsed schedules.
3. Knowledge-base rebuild and retrieval still work with user isolation intact.
4. RAG answer streaming still produces `meta`, `token`, and `done` events with the current SSE semantics consumable by the current frontend.
5. Parse and RAG LangChain-backed code paths are both exercised in tests or targeted smoke verification.
6. AI async paths no longer rely on long-lived dependency-injected DB sessions during external waits.
7. Frontend build passes and ordinary CRUD / sync / share / admin regressions remain green.

## Terminal Verification Snapshot

- This round closed on local-only verification rather than GitHub or cloud deployment.
- Backend verification passed locally with `pytest server/tests -q` against the local PostgreSQL port mapping.
- The backend regression suite still covers auth, CRUD, sync, share, admin, Parse, RAG, and smoke scenarios after the AI-layer refactor.
- Frontend production build passed locally with `docker compose exec frontend npm run build`.
- Host-shell `npm run build` was blocked by a local sandbox path-resolution issue on `C:\Users\nor`; the local containerized frontend build is the accepted round-close build artifact for this round.
