# Progress Tracker (R27 - Optional Cloud Email Reminder Wiring)

## Legend

- `[x]` Completed
- `[>]` In progress
- `[ ]` Pending

## Round Rules

- Keep email reminders optional, default-off, and limited to cloud schedules.
- Do not add email as a required auth field.
- Use Brevo HTTP API and do not leak the API key in logs, docs, or commits.
- Keep sending off the main request path through a lightweight scanner/worker loop.
- Do not replace or regress the existing mobile local-notification path.
- Stay local only; implementation, tests, and docs closure are required before closing the round.

- [x] `P1` Docs refresh and planning lock
  - [x] `P1-S1` Refresh active round docs for R27 and lock the optional cloud email reminder boundaries.
  - `done_when`: working_contract, current_state, task_board, and any needed contract docs describe the new round and docs consistency passes.
  - `verification_plan`: docs audit + `python skills/coding-agent-loop/scripts/docs_consistency_check.py --docs-root docs`.

- [x] `P2` Backend reminder foundation
  - [x] `P2-S1` Add minimal config, persistence, and API surfaces for user email config, cloud schedule reminder flags, and reminder records.
  - [x] `P2-S2` Implement Brevo sending and reminder recompute/idempotency rules.
  - `done_when`: backend surfaces can store optional email settings, cloud schedule reminder settings, and due reminder rows without sending on the request path.
  - `verification_plan`: targeted backend tests + code inspection of recompute/send paths.

- [x] `P3` Background scan and minimal frontend entry
  - [x] `P3-S1` Add a lightweight background scan loop that sends due reminders and records send state safely.
  - [x] `P3-S2` Add the smallest frontend controls for user email config and cloud schedule reminder opt-in.
  - `done_when`: a user can configure the email address, enable a reminder on a cloud schedule, and the backend can later send it without blocking CRUD requests.
  - `verification_plan`: local API/manual path checks + frontend build verification.

- [x] `P4` Verification and closeout
  - [x] `P4-S1` Add or update tests for email config, enablement, due-send, reschedule, disable/delete stop, and duplicate-scan idempotency.
  - [x] `P4-S2` Run regression/build/docs checks and document remaining validation limits.
  - `done_when`: targeted tests plus regression/build/docs checks all pass and remaining risks are explicitly recorded.
  - `verification_plan`: `docker compose exec api pytest ...`, `docker compose exec frontend npm run build`, and docs consistency.

- `current_phase`: `P4`
- `current_step`: `P4-S2`
