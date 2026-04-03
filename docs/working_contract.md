# Working Contract (R19 - Parse Follow-Up Context Reinforcement)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` because this round touches Parse multi-turn context packaging and preserved Parse session semantics
5. `docs/decision_log.md` only when the active docs do not fully explain a durable tradeoff from earlier Parse rounds

## Round Origin

- This is Round 19 (R19), opened on 2026-04-03 for the requirement `Parse 多轮追问上下文补强`.
- R18 is terminal historical input only. Its completed docs and implementation are baseline context, not this round's active state.
- Current repo reality already includes:
  - backend-owned Parse session state in memory
  - draft-first confirmation flow and confirm-only persistence
  - field-level `keep / set / clear` draft update semantics
  - model-facing `current_draft`
  - `session_context` with prior user turns, replayed draft snapshots, and field history
- The gap this round closes:
  - short follow-up replies such as `早上九点开始` can still fail to fill the intended missing field
  - current model-facing context does not explicitly provide the preceding assistant follow-up, current `missing_fields`, current `follow_up_questions`, or a clear pending slot cue
  - the problem should be treated first as Parse context orchestration, not as a large heuristic rule expansion

## Planner / Executor / Reviewer Boundary

- Planner refreshes active docs, keeps the round Parse-focused, and defines a small-step execution order that starts from context packaging rather than broad rule growth.
- Executor implements only the active step from `docs/current_state.md`, verifies that step, then updates docs.
- Reviewer checks the active step against `done_when` and `verification_plan`, with special focus on:
  - whether short follow-up answers are grounded in the latest assistant question and current missing slots
  - whether `keep / set / clear` behavior remains intact
  - whether simple one-shot Parse and draft-first confirm-only flow remain unchanged externally

## Core Constraints

- Preserve the current draft-first Parse workflow.
- Preserve user-confirmed save behavior for AI-parsed schedules.
- Preserve the existing Parse frontend/API contract unless a minimal additive alignment is strictly required.
- Do not turn Parse into a general chatbot.
- Do not widen this round into RAG, sync, CRUD, share, auth, or admin work.
- Do not rely on a broad new batch of heuristic time rules as the primary fix.
- Do not patch large amounts of Chinese time-expression handling just to make this scenario pass.
- Prefer incremental context-packaging changes in `server/app/services/parse_service.py`.
- `server/app/services/ai_runtime.py` may change only if the Parse runtime seam needs a small payload-shape adjustment.
- Keep the implementation understandable and testable.
- Do not modify `prompts/`, `media/`, or `skills/`.
- Do not perform cloud deployment in this round.

## Protected Paths

- `prompts/`
- `media/`
- `skills/`

## Scope Definition

### In scope

- `server/app/services/parse_service.py`
- `server/app/services/ai_runtime.py` only if the Parse runtime seam needs a minimal payload-shape or invocation adjustment
- Parse-related tests
- `docs/current_state.md`
- `docs/task_board.md`
- `docs/api_contract.md` only if the internal contract boundary needs clarification
- `docs/decision_log.md` only if a durable cross-round design choice is made

### Out of scope

- broad heuristic-rule expansion for Chinese time parsing
- rebuilding Parse as a general-purpose chat system
- large frontend redesign
- RAG architecture changes
- unrelated backend refactors outside Parse
- cloud deployment or cloud-only validation

## Verification-First Rules

- This round must prove improvement with targeted Parse follow-up tests, not with prompt text alone.
- Backend Parse regression is mandatory for every execution step that changes behavior.
- The round must add or update coverage for at least:
  - first turn `明天到A-201开会`
  - follow-up turn `早上九点开始`
  - expected outcome: `start_time` is filled more reliably and the session can progress toward confirmation
- Existing Parse referential-update regression from R18 must remain green.
- If the LangChain payload shape changes, update or extend the LangChain integration tests accordingly.
- Frontend sanity check is optional and minimal unless a visible contract adjustment becomes necessary.

## Document Synchronization Rules

- This round starts from `PLAN`; do not skip directly to `EXECUTE` or `REVIEW`.
- After each completed step, update `docs/current_state.md` to the next active step.
- Keep exactly two `[>]` entries in `docs/task_board.md` during an active round: one phase and one step.
- Record only durable cross-step decisions in `docs/decision_log.md`.
- If implementation evidence shows the fix requires broader heuristic growth or a frontend/API redesign, route to `REPLAN` instead of silently widening scope.
