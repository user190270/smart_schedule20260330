# Working Contract (R20 - RAG True Streaming Output)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md`
5. `docs/decision_log.md` only if older tradeoffs need explanation

## Round Outcome

- Round 20 (R20) is complete.
- This round corrected the RAG answer path from synthetic SSE token splitting to true streaming after retrieval.
- The preserved boundary remains:
  - retrieval still finishes first
  - the route still emits `meta / token / done`
  - chat history is still available after a successful stream
- The changed boundary is:
  - `token` events now come from the runtime streaming iterator instead of `answer_text.split()`
  - the final answer is accumulated during streaming and saved only after a successful completion
  - the frontend now appends raw streamed chunks instead of forcing a trailing space per token

## Implemented Scope

- `server/app/routers/rag.py`
- `server/app/services/rag_service.py`
- `frontend/src/views/RagView.vue`
- `server/tests/test_rag_workflow.py`
- `server/tests/test_ai_langchain_integration.py`
- active round docs

## Constraints Preserved

- No Parse changes were introduced for this round.
- No RAG route proliferation was introduced.
- The existing SSE event names remain:
  - `meta`
  - `token`
  - `done`
- Retrieval continues to use the existing pgvector-based flow.
- Frontend changes stayed minimal and limited to chunk append behavior and stream-failure messaging.
- No cloud deployment was performed as part of this round.
- `prompts/`, `media/`, and `skills/` remained untouched.

## Verification Summary

- Focused RAG integration tests passed:
  - `docker compose exec api pytest tests/test_ai_langchain_integration.py -q`
  - `docker compose exec api pytest tests/test_rag_workflow.py -q`
- Full backend test suite passed:
  - `docker compose exec api pytest tests -q`
- Frontend build passed:
  - `docker compose exec frontend npm run build`
- Local API health check passed:
  - `GET /api/health`
- Browser-tool page sanity verification was attempted but the local Playwright session failed before navigation, so the round relies on route-level streaming tests plus frontend build verification rather than a completed browser walkthrough.

## Durable Takeaway

- This round is evidence-backed for "real streaming output" only because the backend route now forwards runtime chunks directly.
- Future rounds should preserve this distinction and avoid reintroducing display-only fake streaming.
