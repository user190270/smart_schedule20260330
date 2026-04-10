# Current State

## Read Policy

- Read `docs/working_contract.md`, `docs/current_state.md`, and `docs/task_board.md` first.
- Read `docs/api_contract.md` only if interface implications need clarification.
- Read `docs/decision_log.md` only if an older tradeoff must be explained.

## Round Context (R27 - Optional Cloud Email Reminder Wiring)

- `mode`: `TERMINAL`
- `project_title`: `Smart Schedule MVP - Optional Cloud Email Reminder Wiring`
- `round_target`: `Add an optional Brevo-backed cloud email reminder path with minimal user and cloud schedule configuration, separate background sending, and local verification only.`

## Execution Status

- `current_phase`: `P4`
- `current_step`: `P4-S2`
- `status`: `completed`

## Delivered State

- Optional cloud email reminders now exist as a default-off sidecar feature.
- Users can save or clear an optional notification email address without changing login/register required fields.
- Cloud schedules can opt into email reminders with the preset lead-time list `0 / 1 / 5 / 10 / 30`.
- Reminder scheduling is persisted separately from schedules through `email_reminders`, and due-send work happens on the background scan path rather than inline with request handlers.
- Schedule create/update/delete and reminder enable/disable flows recompute or deactivate reminder rows, and repeated scans do not resend already-sent reminders.
- Existing auth, schedule, Parse, RAG, sync, share, and mobile local-notification mainline behavior remains intact in local regression/build verification.

## Plan

### P1 - Docs refresh and boundary lock
- `P1-S1`: Refresh active docs for R27 and lock the optional-email-reminder scope before editing code. Completed.

### P2 - Backend reminder foundation
- `P2-S1`: Add minimal config, schema, and persistence surfaces for optional user email config, cloud schedule reminder flags, and reminder records. Completed.
- `P2-S2`: Add Brevo HTTP sending plus reminder recompute rules and idempotent reminder record management. Completed.

### P3 - Background scan and minimal frontend entry
- `P3-S1`: Add a lightweight background reminder scanner that sends due emails off the main request path. Completed.
- `P3-S2`: Add the smallest frontend UI needed to edit the user email address and opt cloud schedules into reminder sending. Completed.

### P4 - Verification and closeout
- `P4-S1`: Add targeted tests for email config, reminder creation/recompute/deactivation, due-send behavior, and duplicate-scan idempotency. Completed.
- `P4-S2`: Run regression/build/docs checks and record remaining validation limits or risks. Completed.

## Done When

- A user can configure an optional email address without changing the auth required fields.
- A cloud schedule can opt into email reminders with one preset lead-time value.
- Future reminders create or update persisted reminder rows; edits/deletes/disabling deactivate or recompute them correctly.
- The background scan sends due reminders through Brevo without blocking request handlers.
- Repeated scans do not resend the same reminder.
- Existing core auth, schedule, Parse, RAG, sync, share, and mobile local-notification flows still pass regression checks.

## Verification Results

- `docker compose exec api pytest /app/tests -q`: `59 passed`
- `docker compose exec frontend npm run build`: passed
- `python skills/coding-agent-loop/scripts/docs_consistency_check.py --docs-root docs`: passed after closeout updates

## Remaining Validation Limits

- Local automated verification covers the backend reminder lifecycle and frontend build, but it does not prove real delivery against a live Brevo request inside the test suite.
- The Android/Capacitor side of the existing local-notification path was not re-verified on device in this round; the goal here was to ensure the new email reminder sidecar did not regress that path.
- The minimal frontend gating keeps email reminders meaningful only for cloud-backed schedules; deeper UX polish or richer reminder products remain intentionally out of scope.
