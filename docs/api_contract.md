# API Contract (R27 - Optional Cloud Email Reminder Additions)

## Scope

- This round adds a small cloud email reminder contract surface.
- Auth login/register credentials remain unchanged.
- Existing Parse / RAG / share contracts are untouched.

## Auth / User Settings Boundary

- Registration and login requests remain:
  - `username`
  - `password`
- The user profile response may be extended with an optional notification email field.
- A minimal authenticated profile/settings update endpoint may be added so a user can save or clear that optional email address without involving admin flows.

## Schedule Boundary

- Cloud schedule request and response shapes may be extended with additive reminder fields:
  - `email_reminder_enabled`
  - `email_remind_before_minutes`
- These fields are optional and default-off.
- Valid lead values are restricted to:
  - `0`
  - `1`
  - `5`
  - `10`
  - `30`
- Reminder settings only apply meaningfully to cloud schedules.

## Sync Boundary

- If sync payload changes are required for correctness, they must stay additive and mirror the same schedule reminder fields.
- If a minimal implementation can avoid sync contract changes safely this round, prefer that narrower path.

## Reminder Execution Boundary

- Reminder scheduling and sending remain server-side concerns.
- Request handlers may create/update/deactivate reminder records, but they must not send emails inline.
- Actual email delivery occurs on a background scan path and must be idempotent.

## Compatibility Guardrails

- Existing auth required fields do not change.
- Existing schedule CRUD remains valid when reminder fields are omitted.
- Existing mobile local notifications remain separate and must continue to work.
- Existing Parse, RAG, sync, share, and admin contracts must not regress as part of this round.
