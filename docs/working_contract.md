# Working Contract (R17 - LangChain Integration and Async AI Service Hardening)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` because this round touches AI, async service boundaries, and streaming contracts
5. `docs/decision_log.md` only when the active docs do not fully explain a durable route choice

## Round Origin

- This is Round 17 (R17), opened on 2026-04-01 for the requirement `LangChain integration and AI service-layer async hardening`.
- R16 is historical input only. Its active docs must not be reused as this round's live state.
- Current repo has a rollback checkpoint at commit `927c089` with message `chore: checkpoint after web desktop polish`.
- Current repo reality already includes:
  - local-first schedules
  - Push / Pull and sync status aggregation
  - knowledge-base rebuild and pgvector-backed retrieval
  - Parse agent multi-turn session flow
  - admin Web page
- The gap this round closes:
  - `server/pyproject.toml` does not yet include LangChain dependencies
  - Parse and RAG still rely on a synchronous custom provider path
  - AI upstream calls do not yet form a trustworthy async, non-blocking chain
  - the code cannot yet honestly claim that AI orchestration is LangChain-based or that long AI waits are isolated from ordinary transactional paths

## Planner / Executor / Reviewer Boundary

- Planner refreshes active docs, locks the LangChain + async AI scope, and defines step-level acceptance criteria.
- Executor implements only the active step from `docs/current_state.md`, verifies that step, then updates docs.
- Reviewer checks the active step against `done_when` and `verification_plan`, with special focus on:
  - real LangChain execution rather than comments or wrappers
  - real async await paths rather than nominal `async def` wrappers around blocking work
  - preserving Parse / RAG contract compatibility

## Core Constraints

- Do not modify `prompts/`, `media/`, or `skills/`.
- Do not regress existing Parse semantics:
  - multi-turn session state
  - draft update flow
  - follow-up questions
  - `ready_for_confirm`
  - confirm-only persistence for AI parsed schedules
- Parse and RAG must both land on real LangChain-backed orchestration by round close. Finishing only one of them is not sufficient for this round.
- Do not break the current RAG retrieval contract or the `/api/rag/answer/stream` SSE event semantics / frontend consumption pattern.
- Do not replace PostgreSQL + pgvector retrieval with a different vector-store architecture.
- Do not rewrite the entire backend into a full async system. Ordinary CRUD / sync / share / admin paths stay on their current architecture unless a minimal compatibility adjustment is strictly required.
- AI-path async means real awaited external model / embedding calls, not only route signatures.
- AI routes must not keep a long-lived dependency-injected database session alive while awaiting external model work. If needed, services should use short-lived read / write sessions around the external await.
- LangChain usage must be real code-level orchestration in Parse and/or RAG, not documentation theater.
- New dependencies must remain reasonably scoped and compatible with the current server runtime.

## Protected Paths

- `prompts/`
- `media/`
- `skills/`
- Executor must not modify `docs/working_contract.md` unless a future replan explicitly requires it.

## Scope Definition

### In scope

- `server/pyproject.toml` and backend AI dependency wiring
- `server/app/services/` AI provider / orchestration / runtime modules
- `server/app/routers/parse.py`
- `server/app/routers/rag.py`
- `server/app/core/database.py` or adjacent helpers when needed to shorten AI-path DB session lifetime
- backend AI tests and active docs

### Out of scope

- changing `prompts/`, `media/`, or `skills/`
- replacing pgvector SQL retrieval
- introducing Celery, Kafka, message queues, or background worker infrastructure
- removing the AI draft confirmation gate
- broad refactors of ordinary CRUD / sync / share / admin code for style alone

## Verification-First Rules

- Every AI step must prove both behavior and architecture:
  - behavior: Parse session semantics and RAG SSE contract still work
  - architecture: LangChain objects are actually executed in both Parse and RAG, async await paths are real, and DB session boundaries are shorter and clearer
- Backend verification is mandatory for every AI step.
- Final round-close verification must include:
  - backend tests or targeted critical-path checks
  - manual Parse and RAG smoke validation
  - `npm run build` in `frontend/`
- When a step changes router or service boundaries, document the read -> external await -> write split explicitly in docs or review evidence.

## Document Synchronization Rules

- After each completed step, update `docs/current_state.md` to the next active step.
- Keep exactly two `[>]` entries in `docs/task_board.md` during an active round: one phase and one step.
- Record only durable cross-step decisions in `docs/decision_log.md`.
- If implementation evidence shows the current step cannot preserve Parse / RAG compatibility within this round's constraints, route to `REPLAN` rather than silently broadening scope.
