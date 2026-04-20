# API Contract (R29 - Token-Based AI Quota Correction)

## Scope

- This round corrects the existing authenticated quota/tier contract surface from call-count semantics to token semantics.
- Auth login/register credentials remain unchanged.
- Parse and RAG request shapes should stay stable where possible, but their quota/error surface may change to expose token usage details.

## Auth / User Boundary

- Registration and login requests remain:
  - `username`
  - `password`
- The authenticated user/profile response may expose additive or renamed quota fields such as:
  - `subscription_tier`
  - `daily_token_usage`
  - `daily_token_limit`
  - optional last-reset metadata if needed for UX clarity
- A minimal authenticated quota summary endpoint may be added only if keeping the quota response separate from the profile surface is cleaner than reusing `/auth/me`.
- A minimal authenticated demo-upgrade endpoint may be added so the user can switch to a higher tier without involving admin-only flows or real payment.

## Tier And Limit Boundary

- Tier definitions should stay fixed and server-owned for this round.
- The frontend may request an upgrade target tier, but the backend decides whether the target is valid and what daily limit it maps to.
- The quota limit is a daily token allowance, not a real billing entitlement.
- Existing daily usage/reset persistence should be reused where practical so admin reset remains meaningful.

## Parse / RAG Error Boundary

- Existing Parse and RAG request bodies should remain unchanged if possible.
- When the user has exhausted the daily limit, the API may return an over-limit response, preferably with:
  - a stable machine-readable error code
  - current tier
  - used token quota
  - daily token limit
- The frontend should not have to infer the reason for failure from raw text.
- The same quota semantics should apply to the cloud AI operations that generate query embeddings and rebuild embeddings, even if those routes do not need a new public request shape.

## Time Window Boundary

- The daily quota window must be evaluated on `Asia/Shanghai` natural-day boundaries.
- Persisted timestamps, including `last_reset_time`, remain UTC.
- Admin reset continues to zero the current user's `daily_token_usage` and set a fresh UTC `last_reset_time`.

## Admin Boundary

- Existing admin reset behavior must remain valid.
- If admin responses expose the user's tier or current quota numbers, that change must stay additive.
- This round does not add admin-managed billing tools.

## Compatibility Guardrails

- Existing auth required fields do not change.
- Existing schedule CRUD, sync, share, reminder, and mobile local-notification contracts must not regress as part of this round.
- No payment-provider credentials, checkout flows, or order identifiers should appear in the contract.
