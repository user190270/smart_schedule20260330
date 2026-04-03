# API Contract (R20 Completed)

## Scope

- This file records the finalized contract boundary for the RAG true-streaming round.
- Parse, sync, CRUD, share, auth, and admin contracts remain unchanged.
- The focal route remains `POST /api/rag/answer/stream`.

## Preserved External Contract

- Route:
  - `POST /api/rag/answer/stream`
- SSE event names:
  - `meta`
  - `token`
  - `done`
- Event meaning:
  - `meta`: retrieval summary, especially retrieved chunk count
  - `token`: streamed answer content fragment
  - `done`: terminal stream marker
- Frontend consumer shape in `frontend/src/api/rag.ts` remains compatible with the same event names.

## Corrected Internal Timing Semantics

- Retrieval still completes before answer generation starts.
- After retrieval, the backend now forwards chunks directly from `LangChainAiRuntime.astream_text(...)`.
- `token` events are no longer derived from splitting a completed answer string.
- The route accumulates streamed chunks during generation.
- Chat history is written only after successful stream completion.

## Minimal Additive Behavior

- `done.data.message` now distinguishes:
  - `stream_completed`
  - `stream_failed`
- This is a minimal terminal-state clarification and does not alter the event names or the frontend stream parser shape.

## Frontend Consumption Boundary

- The frontend still consumes the stream through `fetch + getReader + TextDecoder`.
- The main consumption adjustment is append behavior:
  - old behavior: force `"text + space"`
  - new behavior: append raw chunk text as received
- This prevents chunk-join artifacts once the backend switches from word-split fake tokens to real streamed fragments.

## Verification Evidence

- Route-level tests prove:
  - `meta -> token -> done` ordering
  - token events match the runtime chunk sequence exactly
  - final answer accumulation persists the joined answer only after successful completion
  - interrupted streams return `done.message = stream_failed` without persisting a partial assistant answer
