# Current State

## Read Policy

- Read `docs/working_contract.md`, `docs/current_state.md`, and `docs/task_board.md` first.
- Read `docs/api_contract.md` for the preserved Parse / RAG compatibility boundaries and the round-close verification snapshot.
- Read `docs/decision_log.md` only for durable tradeoffs that explain why the final implementation chose a specific boundary.

## Round Context (R17 - LangChain Integration and Async AI Service Hardening)

- `mode`: `TERMINAL`
- `project_title`: `Smart Schedule MVP - LangChain Integration and Async AI Service Hardening`
- `round_target`: `Integrate LangChain into the AI service layer and convert key Parse / RAG upstream paths to async, non-blocking flows that avoid holding database sessions during long external waits, while preserving the existing local-first product contracts.`

## Execution Status

- `current_phase`: `COMPLETED`
- `current_step`: `LOCAL BUILD VERIFIED`
- `status`: `completed`

## Final Repo State

- Rollback checkpoint remains available at `927c089` (`chore: checkpoint after web desktop polish`).
- `server/pyproject.toml` now includes real LangChain dependencies for backend AI orchestration.
- `server/app/services/ai_runtime.py` now provides a shared async LangChain runtime for:
  - structured Parse output
  - text completion / streaming
  - embedding generation
  - normalized AI timeout / availability / upstream error handling
- Parse now uses async route -> service -> runtime calls, keeps the multi-turn parse session workflow, and preserves:
  - draft-first behavior
  - follow-up questions
  - draft patching
  - `ready_for_confirm`
  - confirm-only persistence semantics
- RAG now uses async route -> service -> runtime calls, keeps pgvector retrieval, preserves `/api/rag/answer/stream` event names `meta` / `token` / `done`, and writes chat history only after the AI answer is ready.
- AI routes no longer depend on a long-lived request-scoped DB session during awaited external model work:
  - Parse auth uses a short-lived AI-safe auth lookup
  - RAG uses service-owned `session_scope()` read / write phases around the external await
- Ordinary CRUD, auth, sync, share, and admin API contracts remain locally verified.

## Verification Evidence

- Backend regression suite passed locally against the local Docker PostgreSQL port with:
  - `DATABASE_URL=postgresql+psycopg://smart_schedule:smart_schedule@localhost:5432/smart_schedule`
  - `pytest server/tests -q`
  - result: `45 passed`
- Targeted LangChain coverage is included in `server/tests/test_ai_langchain_integration.py` and passed locally.
- Parse contract regression passed locally with `pytest server/tests/test_parse_contract.py -q`.
- RAG workflow regression passed locally with `pytest server/tests/test_rag_workflow.py -q`.
- Local frontend production build passed via the local containerized frontend environment with:
  - `docker compose exec frontend npm run build`
- No GitHub push, cloud deployment, or public-IP integration was performed in this round; local implementation and local verification are the round-close boundary.

## Compatibility Notes

- Parse fallback heuristics were tightened so session follow-ups preserve prior date intent, ISO datetimes do not mis-parse as clock hours, and location extraction no longer absorbs time fragments.
- `/api/rag/answer/stream` keeps the existing SSE event semantics and current frontend consumption path.
- The backend suite still covers auth, CRUD, sync, sharing, admin, Parse, and RAG after the AI-layer refactor.

## Deferred Follow-Up

- GitHub synchronization is intentionally deferred until after this verified local checkpoint.
- Cloud-agent deployment and public-IP end-to-end validation are intentionally deferred to a later deployment round.
