# Progress Tracker (R13 - Parse Agent Workflow Refactor)

## Legend

- `[x]` Completed
- `[>]` Current
- `[ ]` Pending

## Round Rules

- This round is terminal.
- Future changes must start from a new `PLAN` round instead of reopening these steps in place.

- [x] `P61` Parse agent architecture
  - [x] `P61-S1` Lock the parse session model, action semantics, and backend/frontend ownership boundary
  - [x] `P61-S2` Define the additive or replacement parse-agent API surface and state transitions
  - [x] `P61-S3` Lock save-to-local tool boundaries and storage-strategy handoff
  - `done_when`: the repo has one coherent parse-agent contract covering session state, actions, and confirm-then-save behavior.
  - `verification_plan`: compare current Parse code against the target contract, update docs, and pass docs consistency.

- [x] `P62` Conversation-driven draft update
  - [x] `P62-S1` Implement persistent parse sessions and multi-turn clarification
  - [x] `P62-S2` Replace transcript replay with stateful draft updates driven by session context
  - [x] `P62-S3` Surface missing fields, readiness, and next actions in the UI
  - `done_when`: multi-turn clarification advances one persistent draft session instead of rebuilding from scratch each turn.
  - `verification_plan`: browser-walk a partial prompt, follow-up answer, and subsequent draft update without losing session state.

- [x] `P63` Editable confirmation card
  - [x] `P63-S1` Gate the draft card on structured draft readiness instead of making it a static result block
  - [x] `P63-S2` Preserve user manual edits over later agent updates
  - [x] `P63-S3` Keep storage strategy selection inside the confirmation card
  - `done_when`: the draft card appears when useful, stays editable, and cooperates with ongoing chat turns.
  - `verification_plan`: generate a draft, manually edit fields, continue chatting, and confirm the user edits still win.

- [x] `P64` Tool-call save flow
  - [x] `P64-S1` Formalize `update_draft`, `ask_follow_up`, and `finalize_draft` as explicit agent actions
  - [x] `P64-S2` Add `save_schedule_to_local` as the confirmation-time tool boundary
  - [x] `P64-S3` Preserve existing storage-strategy handoff into local-first / sync / knowledge-base flows
  - `done_when`: agent transitions are action-driven and user confirmation triggers an explicit save-to-local path.
  - `verification_plan`: inspect session/action traces in the UI/backend and confirm saving still lands in the local repository first.

- [x] `P65` Temporal semantics hardening
  - [x] `P65-S1` Require and thread `reference_time` through every parse turn
  - [x] `P65-S2` Improve Chinese relative-time handling and keep `end_time` nullable
  - [x] `P65-S3` Show full year-month-day hour-minute formatting in confirmation state
  - `done_when`: common Chinese relative-time inputs parse more reliably and no fake end-time default remains.
  - `verification_plan`: verify `明早8点到9点在三饭吃饭` and `明天到 A-201 开会` plus empty-end-time save behavior.

- [x] `P66` Acceptance
  - [x] `P66-S1` Browser-verify multi-turn clarification, editable draft, and confirm-to-local save
  - [x] `P66-S2` Verify each storage strategy still flows into the existing sync / knowledge-base mainline
  - [x] `P66-S3` Close the round with build/test evidence and an agent-workflow demonstration path
  - `done_when`: the parse flow is demonstrably a real agent workflow and can credibly be described as an agent project in the resume/demo narrative.
  - `verification_plan`: run the round-close browser path, frontend build, and targeted backend checks.

- `current_phase`: `P66`
- `current_step`: `P66-S3`
