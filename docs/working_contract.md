# Working Contract (R27 - Optional Cloud Email Reminder Wiring)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` only if interface boundaries need confirmation
5. `docs/decision_log.md` only if an older tradeoff must be explained

## Round Goal

Land an optional cloud email reminder capability without disturbing the existing core product paths:

1. Add an optional user notification email configuration.
2. Add opt-in cloud schedule email reminder settings using a small preset lead-time list.
3. Maintain reminder records and send due emails through Brevo on a background scan path.
4. Keep the feature default-off and isolated from auth, Parse, RAG, sync, share, and mobile local-notification mainline behavior.

## Scope

### In Scope
- `server/app/core/config.py`
- `server/app/main.py`
- `server/app/models/...` for the minimal user / schedule / reminder persistence changes
- `server/app/services/...` for reminder recompute, mail sending, and background scanning
- `server/app/routers/auth.py` and/or a nearby minimal user-settings route if needed
- `server/app/routers/schedules.py`
- `server/app/schemas/...` for the smallest contract extensions required by the feature
- `server/alembic/versions/...`
- `server/tests/...` covering reminder scheduling, recompute, send, and idempotency
- minimal frontend wiring for user email config and cloud schedule reminder controls
- active round docs

### Out of Scope
- changes to registration or login required fields
- marketing / batch email / template systems
- Web Push or browser-level scheduled notifications
- replacing existing mobile local notifications
- Parse / RAG / share / admin feature expansion unrelated to reminder settings
- cloud deployment work

## Constraints

- Email reminders must remain optional and default to disabled.
- Only cloud schedules may enable email reminders.
- No full reminder product redesign and no custom arbitrary reminder times this round.
- Reminder lead time stays on a small preset list: `0 / 1 / 5 / 10 / 30` minutes.
- Do not print or persist the full Brevo API key in logs, docs, test output, or commits.
- Sending must happen off the main request path through a separate scanner/worker-style loop.
- Reminder sending must be idempotent; repeated scans must not resend the same reminder.
- Schedule edits, deletes, or reminder disablement must deactivate or recompute outstanding reminder rows correctly.
- Existing auth, schedule CRUD, Parse, RAG, sync, share, and mobile local-notification flows must not regress.

## Minimal Delivery Strategy

- Treat the user email address as an optional profile setting, not an auth requirement.
- Treat cloud schedule reminder configuration as two additive fields:
  - email reminders enabled
  - reminder lead minutes
- Persist reminder executions separately from schedules so due-send state stays explicit and idempotent.
- Recompute reminder rows when cloud schedules are created, updated, deleted, or have reminder settings changed.
- Use a lightweight in-process background scan loop for local development/testing rather than inventing a new infrastructure stack.
- Keep the frontend surface intentionally small: enough to configure an email address and toggle cloud reminder settings on a schedule, nothing more.

## Verification Strategy

- Prove the user email config path works without changing login/register requirements.
- Prove enabling a reminder for a future cloud schedule creates a due reminder record.
- Prove edits reschedule the reminder, deletes/disablement stop it, and repeated scans do not resend it.
- Run targeted backend tests plus existing core regression tests.
- Run frontend build verification with `docker compose exec frontend npm run build`.
- Run `python skills/coding-agent-loop/scripts/docs_consistency_check.py --docs-root docs` before closing the round.
