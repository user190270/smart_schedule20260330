# Working Contract (R29 - Token-Based AI Quota Correction)

## Reading Order
1. `docs/working_contract.md`
2. `docs/current_state.md`
3. `docs/task_board.md`
4. `docs/api_contract.md` only if interface boundaries need confirmation
5. `docs/decision_log.md` only if an older tradeoff must be explained

## Round Goal

Correct the half-built demo quota/tier feature so the system returns to token-based semantics instead of per-call counting:

1. Restore `users.daily_token_usage` to mean the user's cumulative token usage for the current Asia/Shanghai day.
2. Add a lightweight usage ledger so each cloud AI operation can record its real token consumption without introducing billing or payment systems.
3. Keep the demo-only tier/upgrade capability, but make each tier map to a daily token limit rather than a daily call limit.
4. Enforce the quota on every real cloud AI token-consuming path in scope:
   - Parse LLM calls
   - RAG answer LLM calls
   - query embedding
   - rebuild embedding
5. Move the quota-management entry out of the top bar and make it available by clicking the signed-in user's avatar in the home account panel.
6. Preserve strict per-user isolation, existing admin reset behavior, and the rest of the product mainline behavior.

## Scope

### In Scope
- `server/app/models/...` for the minimal token-usage ledger and user-tier persistence changes
- `server/app/services/...` for quota status, demo upgrade handling, Asia/Shanghai reset/accounting, and AI-path enforcement
- `server/app/services/ai_runtime.py` for exposing real usage metadata from chat and embedding calls
- `server/app/routers/auth.py` and/or a nearby authenticated user route for quota status and demo upgrade
- `server/app/routers/parse.py`
- `server/app/routers/rag.py`
- `server/app/schemas/...` for the smallest contract extensions required by the feature
- `server/alembic/versions/...`
- `server/tests/...` covering tier differences, Shanghai-day reset, Parse/RAG/embedding accounting, and upgrade effects
- minimal frontend wiring for an avatar-driven quota management entry, quota display, demo upgrade action, and over-limit feedback
- active round docs

### Out of Scope
- real payment provider integration
- order, invoice, receipt, webhook, or signature-validation systems
- a full commercial membership platform or long-term billing history
- new sharing, sync, reminder, or local-encryption feature work unrelated to quota tiers
- cloud deployment or operations work

## Constraints

- This round is demo-only: do not implement real payment, settlement, or external billing dependencies.
- Tier changes must be explicit simulated upgrades, not hidden admin-only mutations or display-only labels.
- Different tiers must map to different daily token limits.
- The quota-management entry must be reached by clicking the user avatar in the home account panel; do not keep the top-bar quota button.
- The daily quota window must be evaluated on `Asia/Shanghai` local-day boundaries, while persisted timestamps remain UTC.
- Parse, RAG answer, query embedding, and rebuild embedding limits must be enforced on the real cloud AI paths, not only in the UI.
- Over-limit behavior must be explicit in both API responses and frontend user feedback.
- Keep compatibility with the existing daily usage reset/admin reset behavior instead of replacing it with a heavy quota subsystem.
- Use a soft limit strategy: check before the call, then add the real token usage after the call completes, allowing the final successful call to cross the limit slightly.
- All quota reads and writes must stay strictly bound to the authenticated `user_id`.
- Do not leak secrets in logs, docs, test output, or commits.
- Existing auth, schedule CRUD, sync, share, reminder, Android local notification, and public-share flows must not regress.

## Minimal Delivery Strategy

- Model a small fixed demo tier set, such as free vs higher paid/demo tiers, and derive the daily token limit from that tier.
- Prefer additive user fields plus one lightweight usage-event table over introducing a new billing table family.
- Reuse the existing daily usage/reset path where possible so admin reset remains meaningful.
- Add one authenticated quota summary surface and one authenticated demo-upgrade surface instead of inventing a payment flow.
- Enforce quota before real cloud AI execution, then account for successful calls on completion using real token usage from the runtime.
- Keep the frontend surface intentionally small: an avatar click entry, quota status display, and a demo upgrade action.

## Verification Strategy

- Prove different tiers resolve to different daily token limits.
- Prove over-limit requests are blocked on Parse.
- Prove over-limit requests are blocked on RAG answer.
- Prove query embedding and rebuild embedding are recorded against the current user.
- Prove a demo upgrade changes the effective limit for the user.
- Prove Asia/Shanghai daily reset logic still works correctly while persisted timestamps remain UTC.
- Prove the quota-management entry is reachable from the account avatar and no longer exposed in the top bar.
- Run targeted backend tests plus selected core regression tests.
- Run frontend build verification with `docker compose exec frontend npm run build`.
- Run `python skills/coding-agent-loop-en/scripts/docs_consistency_check.py --docs-root docs` during planning and before closeout.
