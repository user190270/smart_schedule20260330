# Working Contract (R32 - Local Schedule Overlap Warning)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` only if interface boundaries unexpectedly change
5. `docs/decision_log.md` only if a new tradeoff must be recorded

## Round Goal

Add a non-blocking local schedule overlap warning for create/edit flow:

1. Detect overlap against current local visible schedules before save.
2. Treat `end_time = null` as a point-in-time event rather than an open-ended interval.
3. Warn the user which schedules overlap, but do not hard-block saving.
4. Use a save-before-continue warning flow:
   - detect overlap
   - show warning sheet
   - let the user choose continue-save or return-to-edit
5. Keep all existing local-first, sync-conflict, and backend behavior unchanged.

## Scope

### In Scope
- `frontend/src/stores/local-schedules.ts`
- `frontend/src/views/ScheduleView.vue`
- optional small supporting type additions in frontend local-schedule modules if needed
- active round docs

### Out of Scope
- backend APIs, schemas, or persistence contracts
- database migrations
- sync conflict semantics
- parse, rag, share, quota, or reminder logic beyond keeping current behavior intact
- complex overlap comparison UI

## Constraints

- Overlap is warning-only, not a hard validation error.
- Keep `sync_intent = conflict` reserved for local/cloud sync conflicts; do not reuse it for time overlap.
- Detection must ignore deleted records.
- Detection must ignore the record being edited.
- Detection must use current-account visible local records, not only the currently filtered list in the page.
- Interval semantics are half-open:
  - interval = `[start_time, end_time)`
  - touching endpoints do not count as overlap
- Point-event semantics:
  - `end_time = null` means a single time point at `start_time`
  - point vs interval overlaps when `start <= point < end`
  - point vs point overlaps only when timestamps are equal
- UI must stay simple:
  - warning title
  - list of overlapping schedule title + time
  - continue-save / return-to-edit

## Minimal Delivery Strategy

- Add a pure overlap detection helper and a store-facing overlap query method first.
- Integrate the editor submit flow afterward, without changing the store's save semantics.
- Reuse existing popup patterns in `ScheduleView.vue` instead of inventing a new page or complex compare component.
- Verify with targeted frontend build and docs consistency check.

## Verification Strategy

- Prove overlap is detected for:
  - interval vs interval
  - point vs interval
  - point vs point
- Prove endpoint-touching schedules do not warn.
- Prove edit flow skips the record being edited.
- Prove deleted records do not participate.
- Prove continue-save still persists successfully after warning.
- Run frontend build verification.
- Run `python skills/coding-agent-loop-en/scripts/docs_consistency_check.py --docs-root docs`.
