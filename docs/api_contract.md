# API Contract (R13 Active)

## Scope

- This file is the active boundary for the parse-agent refactor round.
- Existing local-first schedules, Push / Pull, knowledge-base rebuild, RAG, auth, and sharing flows remain in force.
- This round changes the parse workflow from a one-shot extraction model to a stateful agent model.

## Current Gap To Close

- The current frontend Parse page looks conversational but still works by replaying the transcript into `POST /api/parse/schedule-draft`.
- The current backend stream endpoint is an SSE wrapper around the same one-shot draft generation.
- That means the current system does not yet satisfy the target definition of an agent workflow.

## Parse Agent Session Contract

- Parse must become session-based.
- Minimum state carried across turns:
  - `parse_session_id`
  - ordered `messages`
  - `draft`
  - `missing_fields`
  - `ready_for_confirm`
  - `next_action`
  - action/tool trace sufficient to explain draft progression
- The session state must survive across multiple turns in a way that is not equivalent to client-side transcript replay alone.

## Draft Shape Contract

- Minimum draft fields:
  - `title`
  - `start_time`
  - `end_time`
  - `location`
  - `remark`
  - `source`
  - `storage_strategy`
- `end_time` is nullable across parse, confirmation, and persistence.
- Time values must remain compatible with the existing schedule/local-store pipeline.

## Action / Tool Contract

- The parse workflow must expose explicit action semantics, not only raw chat text.
- Minimum agent actions/tools for this round:
  - `update_draft`
  - `ask_follow_up`
  - `finalize_draft`
  - `save_schedule_to_local`
- Optional later actions may include:
  - `choose_storage_strategy`
  - `schedule_push_hint`
- User confirmation is required before `save_schedule_to_local`.

## Frontend Parse Contract

- Parse page exposes one primary user-facing action: `智能解析`.
- Frontend must send `reference_time` on every start / continue turn.
- Frontend must render:
  - conversation history
  - draft readiness state
  - missing fields
  - editable draft card when the session has enough structure
- User manual edits must take precedence over later agent updates unless the user changes the field again.

## Backend Parse Contract

- The round target assumes explicit backend participation in parse session state rather than pure frontend-only orchestration.
- Backend parse handling must therefore be able to:
  - create a new parse session
  - accept follow-up turns for an existing session
  - return the updated draft/session state
  - finalize a draft once ready
- Route names may be additive or may replace the old one-shot shape during execution, but the resulting contract must express session state explicitly.

## Persistence Contract

- AI output is always draft state first, never an immediate persisted schedule.
- After user confirmation, the save tool must create a local schedule record first.
- The selected storage strategy must then continue through the existing semantics:
  - `local_only`
  - `sync_to_cloud`
  - `sync_to_cloud_and_knowledge`
- Parse refactor must not bypass or replace the local-first repository.

## Time Semantics Contract

- `reference_time` is a required product input for all parse turns.
- Relative Chinese time expressions must be interpreted from `reference_time` and timezone context.
- Draft confirmation state must show full year-month-day hour-minute formatting.
- Missing `end_time` must display as `未设置结束时间` or an equivalent explicit empty-state label.
- The system must not auto-fill `23:59:59` or another fake precise end time without user confirmation.

## Verification Contract

- Required round-close browser acceptance:
  1. start one parse session with `明早8点到9点在三饭吃饭`
  2. verify a reasonable draft is formed and can be saved
  3. start another parse session with `明天到 A-201 开会`
  4. verify follow-up behavior for missing fields and allow nullable `end_time`
  5. continue the same session with another user reply and confirm the draft advances instead of resetting
  6. manually edit the draft card and confirm manual overrides are preserved
  7. save through each storage strategy path and confirm the existing local-first downstream behavior still works
