# Working Contract (R18 - Parse Referential Context and Partial Update Hardening)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` because this round touches Parse session semantics and preserved frontend/backend compatibility
5. `docs/decision_log.md` only when the active docs do not fully explain a durable Parse route choice

## Round Origin

- This is Round 18 (R18), opened on 2026-04-02 for the requirement `Enhance Parse multi-turn context understanding and referential update behavior`.
- R17 is terminal historical input only. Its active docs must not be reused as this round's live state.
- Current repo reality already includes:
  - backend-owned Parse session state
  - draft-first confirmation flow
  - session follow-up questions and `ready_for_confirm`
  - frontend Parse chat transcript plus draft confirmation card
  - LangChain-backed Parse runtime seam from the prior round
- The gap this round closes:
  - model-facing Parse context still centers on `latest_user_message + current_draft`
  - session history is retained mostly for display and remark composition rather than reliable referential reasoning
  - field merge behavior is too coarse for instructions like `keep prior time`, `only change location`, `clear end time`, or `reuse the earlier place`

## Planner / Executor / Reviewer Boundary

- Planner refreshes active docs, locks the Parse-only scope, and defines a small-step execution order.
- Executor implements only the active step from `docs/current_state.md`, verifies that step, then updates docs.
- Reviewer checks the active step against `done_when` and `verification_plan`, with special focus on:
  - real referential multi-turn improvement rather than prompt-only wording changes
  - field-level add / replace / keep / clear semantics
  - preserving simple one-shot Parse behavior and confirm-only persistence

## Core Constraints

- Preserve the current draft-first Parse workflow.
- Preserve user-confirmed save behavior for AI-parsed schedules.
- Do not turn Parse into a general chatbot.
- Do not let AI overwrite unrelated fields during partial updates unless the latest user message clearly replaces them.
- Referential instructions must be handled more intentionally across turns, including:
  - reuse of earlier time or location
  - partial replacement of one field while keeping others
  - explicit clearing such as `不要结束时间了`
- Prefer incremental changes in `server/app/services/parse_service.py` over a large rewrite.
- `server/app/services/ai_runtime.py` may change only if the Parse payload seam needs a small, testable extension.
- Preserve current Parse route compatibility and frontend Parse page behavior unless a minimal additive change is strictly required.
- Do not regress existing Parse simple one-shot behavior.
- Do not break existing RAG, sync, CRUD, share, or admin contracts.
- Do not modify `prompts/`, `media/`, or `skills/`.

## Protected Paths

- `prompts/`
- `media/`
- `skills/`
- Large frontend redesign is prohibited in this round.

## Scope Definition

### In scope

- `server/app/services/parse_service.py`
- `server/app/services/ai_runtime.py` only if the Parse runtime seam needs a payload-shape adjustment
- Parse-related schemas, route compatibility, and tests
- Minimal Parse frontend/client alignment only if backend behavior requires a small additive UI or contract adjustment

### Out of scope

- rebuilding Parse as a general-purpose chat system
- changing RAG architecture
- broad backend refactors outside Parse unless strictly required
- unrelated schedule schema expansion
- visual frontend redesign

## Verification-First Rules

- Backend Parse regression is mandatory for every execution step in this round.
- This round must add or update targeted tests for representative referential scenarios, including:
  - initial message plus time follow-up
  - keep prior time and change only location
  - clear end time only
  - retain title and location while replacing time
  - reuse of earlier context across turns
- Final round-close evidence must show:
  - simple one-shot Parse still works
  - draft-first and confirm-only persistence still hold
  - referential updates avoid clobbering unrelated fields
- Frontend sanity check is only required if contract or UI behavior changes.

## Document Synchronization Rules

- After each completed step, update `docs/current_state.md` to the next active step.
- Keep exactly two `[>]` entries in `docs/task_board.md` during an active round: one phase and one step.
- Record only durable cross-step decisions in `docs/decision_log.md`.
- If implementation evidence shows the current step requires a broader contract shift than planned, route to `REPLAN` rather than silently widening scope.
