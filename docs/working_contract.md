# Working Contract (R13 - Parse Agent Workflow Refactor)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` when work touches parse session architecture, local save flow, schedule schema, storage strategy, or time semantics
5. `docs/decision_log.md` only when the active docs do not fully explain a durable route choice

## Round Origin

- This is Round 13 (R13), opened on 2026-03-27 for the requirement `日程解析 Agent 化重构`.
- R12 is historical input only. Its active docs must not be reused as this round's live state.
- Current repo reality already includes:
  - local-first schedules, Push / Pull, knowledge-base rebuild, RAG, and sharing
  - a Parse page that looks conversational
  - a one-shot backend parse service plus an SSE wrapper
- The gap this round closes is that the existing parse flow is still not a real agent workflow:
  - there is no persisted `parse_session_id`
  - each turn still replays the transcript into a one-shot parse request
  - follow-up is presentation only, not stateful clarification
  - the draft card is editable in UI but not backed by explicit agent actions or a persistent parse session state

## Planner / Executor / Reviewer Boundary

- Planner refreshes active docs, locks the parse-agent architecture, and defines acceptance.
- Executor implements only the active step from `docs/current_state.md`, verifies that step, then updates docs.
- Reviewer checks the active step against `done_when` and `verification_plan`, then routes to approve, rework, or replan.

## Core Constraints

- Keep the existing FastAPI app in `server/app/` as the only backend.
- Keep the current local-first schedule repository and current Push / Pull / knowledge-base / share mainline intact.
- Do not modify `prompts/`, `media/`, or `skills/`.
- Do not keep two user-visible parse modes.
- Do not fake an agent by replaying the whole transcript into the same one-shot parse call every round.
- Do not save schedules before explicit user confirmation.
- Do not auto-fill `end_time` with a fake precise default such as `23:59:59`.
- Parse confirmation must still land in the local repository first, then rely on the existing storage-strategy-driven sync / knowledge-base chain.
- Chinese relative-time understanding must be anchored by explicit `reference_time` and current timezone context.

## Architecture Contract

- Parse is upgraded from `one-shot extraction with follow-up hints` to `sessioned agent workflow`.
- The active target workflow is:
  1. `user_message`
  2. `agent reasoning over current draft + missing fields`
  3. `agent action selection`
  4. `draft update / follow-up question / finalize`
  5. `user confirm`
  6. `save_schedule_to_local`
- This round treats explicit parse session state as a first-class backend contract, not just a frontend convenience cache.
- Minimum state concepts that must exist across turns:
  - `parse_session_id`
  - ordered conversation history
  - current structured draft schedule state
  - missing-field list
  - `ready_for_confirm`
  - recommended next action
  - tool/action trace sufficient to explain why the session moved forward

## UX Contract

- Parse page exposes one primary user action: `智能解析`.
- The page is chat-first by default.
- The draft card is not always visible; it appears only after the agent has enough structured draft state.
- The draft card must remain editable and must cover at least:
  - title
  - start time
  - end time
  - location
  - remark
  - storage strategy
- Agent updates and manual edits must cooperate:
  - agent clarification can update untouched fields
  - user-edited fields win unless the user intentionally changes them again

## Time Semantics Contract

- Frontend must send `reference_time` on every parse / continue turn.
- Backend must interpret common Chinese relative-time phrases using `reference_time` and timezone context.
- `end_time` is nullable across parse, UI, and persistence.
- Missing `end_time` may trigger a follow-up question, but the user may leave it empty.
- Draft confirmation UI must show full year-month-day hour-minute formatting.

## Verification-First Rules

- Every implementation step must include concrete verification before it is marked done.
- Frontend-touching steps must run `npm run build` in `frontend/`.
- Backend parse or schema steps must run targeted backend tests or compile/test validation.
- Required round-close acceptance path:
  1. open Parse page
  2. send `明早8点到9点在三饭吃饭`
  3. verify a reasonable draft is formed and can be confirmed
  4. send an incomplete request such as `明天到 A-201 开会`
  5. verify the agent asks follow-up questions instead of pretending the draft is complete
  6. continue the conversation and verify the same draft session advances instead of resetting
  7. manually edit the draft card and confirm user edits are preserved
  8. save to local with each storage strategy path
  9. confirm the saved record still enters the existing local-first / sync / knowledge-base chain correctly

## Document Synchronization Rules

- After each completed step, update `docs/current_state.md` to the next active step.
- Keep exactly two `[>]` entries in `docs/task_board.md` during an active round: one phase and one step.
- Update `docs/api_contract.md` whenever parse session shape, tool semantics, save flow, or time semantics change.
- Record only durable cross-step decisions in `docs/decision_log.md`.
