# Decision Log

## Read Policy

- Read this file only when `working_contract/current_state/task_board` cannot explain why a route was chosen.
- This file captures durable tradeoffs and execution pivots.

## Entry Template

- `id`
- `status`
- `decision`
- `reason`
- `impact`

## Active Decisions

### D-019

- `status`: active
- `decision`: R2 must restart from `PLAN`; previous round docs are historical anchors only.
- `reason`:
  - User explicitly required rebuilding active docs for the new round.
- `impact`:
  - R2 execution and review routing follow newly rebuilt active docs.

### D-020

- `status`: active
- `decision`: Prioritize MVP delivery quality over skill-system polishing in this round.
- `reason`:
  - User goal is demo-ready and resume-ready product outcome first.
- `impact`:
  - Work breakdown and acceptance focus on runnable loops and reproducibility.

### D-021

- `status`: active
- `decision`: Adopt username/password + JWT access token; no refresh token in R2.
- `reason`:
  - Need to replace `X-User-Id` quickly with formal auth while controlling complexity.
- `impact`:
  - Added `/api/auth/register`, `/api/auth/login`, `/api/auth/me`.
  - Protected endpoints use Bearer auth.

### D-022

- `status`: active
- `decision`: Move formal schema lifecycle to Alembic and stop runtime reliance on `create_all`.
- `reason`:
  - Need auditable, repeatable, migration-driven schema management.
- `impact`:
  - Baseline migration created and startup path shifted to migration-first.

### D-023

- `status`: active
- `decision`: Integrate OpenAI-compatible provider abstraction for Parse/RAG.
- `reason`:
  - Placeholder AI paths are insufficient for MVP demonstration quality.
- `impact`:
  - Provider env-driven runtime path introduced.
  - Parse/RAG services route to provider when configured and report provider failures clearly.

### D-024

- `status`: superseded by D-028
- `decision`: Absorb `agent-c` frontend code selectively after contract review; do not trust docs blindly.
- `reason`:
  - `agent-c` docs are non-authoritative and had API contract drift risks.
- `impact`:
  - Agent-a contract remains source-of-truth for integration.

### D-025

- `status`: active
- `decision`: R2 exit quality gate must include Docker E2E and repeatable smoke checks.
- `reason`:
  - User wants self-reproducible verification, not one-off local success.
- `impact`:
  - P11 includes startup/log/API/UI cross-verification as explicit acceptance criteria.

### D-026

- `status`: active
- `decision`: Add migration bootstrap before app startup to support legacy sqlite volumes during Alembic adoption.
- `reason`:
  - Existing volumes from old `create_all` flow can conflict with first Alembic upgrade.
  - `alembic_version` edge cases (table exists but empty) must be handled.
- `impact`:
  - Startup now runs `python -m app.scripts.bootstrap_migrations`.
  - Legacy complete schema can be stamped then upgraded safely.

### D-027

- `status`: active
- `decision`: Enable backend CORS for local frontend origins and add `httpx` dependency for containerized test execution.
- `reason`:
  - Browser smoke exposed CORS block despite healthy API.
  - Starlette `TestClient` in Docker tests requires `httpx`.
- `impact`:
  - Frontend can call backend from `localhost:5173`.
  - Dockerized backend unit tests are runnable and passing.

### D-028

- `status`: active
- `decision`: R3 adopts agent-c frontend as the visual baseline going forward. Agent-c docs (current_state, task_board, etc.) are NOT trusted as active state — only the code is.
- `reason`:
  - User explicitly designated agent-c frontend as the selected consolidation direction.
  - Agent-c docs may contain inaccuracies or drifts that were never verified against code.
- `impact`:
  - R3 planning is built from a fresh code audit, not from any prior docs.
  - Frontend starting point is the agent-c codebase as-is in `frontend/src/`.

### D-029

- `status`: active
- `decision`: User's suggested P17 "frontend consolidation into mainline" is skipped because agent-c repo IS the mainline for this round.
- `reason`:
  - We are already working in the agent-c repo. The frontend code is already here.
  - No cross-repo merge is needed within this conversation's scope.
- `impact`:
  - Phase numbering starts at P17 but first phase focuses on auth/admin completeness instead of consolidation.

### D-030

- `status`: active
- `decision`: Skill/script system optimization is explicitly deferred from this round.
- `reason`:
  - User constraint: "不要规划 skill/脚本体系优化，先优先把项目做完整".
- `impact`:
  - No changes to `skills/`, `prompts/`, or coding agent loop infrastructure.

### D-031

- `status`: active
- `decision`: Keep `vector_chunks.embedding` stored as `vector(3072)` but implement the HNSW retrieval index on a `halfvec(3072)` expression.
- `reason`:
  - The round target fixes embedding size at 3072 for `gemini-embedding-001`.
  - Live PostgreSQL verification rejected a direct HNSW index on `vector(3072)` because the index dimension limit is lower than 3072.
- `impact`:
  - Storage remains `vector(3072)` to match the product contract.
  - Alembic creates `ix_vector_chunks_embedding_hnsw` on the cast path.
  - Retrieval queries cast both stored embeddings and the query vector to `halfvec(3072)` so PostgreSQL can use the HNSW index.

### D-032

- `status`: active
- `decision`: Round 5 must restart from `PLAN`; Round 4 active docs are historical input only.
- `reason`:
  - The PostgreSQL + pgvector migration round is terminal and already verified.
  - The new requirement changes product semantics and user-visible closure behavior rather than extending the old active step.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new active round.
  - Executors must not treat the old terminal R4 docs as the live step state.

### D-033

- `status`: active
- `decision`: `Push`, `Pull`, and `Rebuild Knowledge Base` are separate first-class user actions and must remain explicit in both contract and UI.
- `reason`:
  - The current product confusion comes partly from collapsing refresh, sync, and index-building semantics into ambiguous actions.
  - The user explicitly rejected continuing to package a plain refresh as sync.
- `impact`:
  - The schedule-page fake sync button must be removed in execution.
  - Backend and frontend work in this round must preserve three distinct action semantics.

### D-034

- `status`: active
- `decision`: Cloud schedule/index counts and knowledge-base rebuild state are backend-owned truth; `last_push_at` and `last_pull_at` may remain client-owned metadata unless later execution proves a backend source is necessary.
- `reason`:
  - Users need truthful cloud/index visibility that local cache alone cannot guarantee.
  - Push and pull timestamps still describe a device-local action history and can stay local without redefining cloud truth.
- `impact`:
  - This round plans an additive backend status contract for cloud and knowledge-base state.
  - Frontend sync status UI may read local timestamps from IndexedDB/local metadata, but must not invent cloud/index counts from local state alone.

### D-035

- `status`: active
- `decision`: Persist only the latest knowledge-base rebuild summary per user in `knowledge_base_states`, while deriving live schedule/chunk counts from relational tables.
- `reason`:
  - The UI needs durable `last rebuild time/status/message` even when the latest rebuild fails and no fresh chunks are written.
  - Live cloud schedule counts and indexed chunk counts should stay query-derived so they do not drift after edits or deletes.
- `impact`:
  - R5 adds the `knowledge_base_states` table plus `/api/sync/status`.
  - Rebuild routes update the latest summary state, while status counts still come from `schedules` and `vector_chunks`.

### D-036

- `status`: active
- `decision`: Round 6 must restart from `PLAN`; Round 5 terminal docs are historical input only.
- `reason`:
  - The new requirement changes product behavior around local ownership and sharing usability instead of extending the already-closed R5 loop.
  - Reusing the terminal R5 active state would hide new constraints and produce an unsafe implementation starting point.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new active round.
  - Executors must not treat R5 terminal state as the live next step.

### D-037

- `status`: active
- `decision`: Keep the existing `share_uuid` public mechanism and prohibit user-visible exposure of internal integer `schedule.id`.
- `reason`:
  - Users should share schedules through a productized visual flow, not by typing database identifiers.
  - The current backend already has a correct public sharing identity, so the usability gap is primarily in the product surface.
- `impact`:
  - The share UI must switch to schedule selection from cloud schedule data.
  - Any internal use of numeric IDs must stay hidden behind the frontend implementation and existing protected API.

### D-038

- `status`: active
- `decision`: Local schedules become a first-class frontend data domain, not just draft or cache state.
- `reason`:
  - The product requirement explicitly restores local-first behavior, including usable CRUD while logged out or offline.
  - The current generic key-value local store and cloud-cache semantics are insufficient to express schedule ownership, edit state, or visibility.
- `impact`:
  - This round plans a dedicated local schedule repository abstraction.
  - Web uses IndexedDB and the Capacitor path must preserve a SQLite-oriented adapter boundary.

### D-039

- `status`: active
- `decision`: Logged-out users may use local schedule CRUD, while `Push`, `Pull`, share creation, knowledge-base rebuild, and RAG remain authenticated cloud actions.
- `reason`:
  - Local-first should improve offline and logged-out usability without weakening cloud ownership or exposing protected resources.
  - The previous route/auth behavior blocked schedule usefulness entirely when not logged in.
- `impact`:
  - The schedule page and local repository work must decouple local CRUD from backend auth.
  - Sync/share/knowledge-base surfaces must continue to show clear auth-gated behavior.

### D-040

- `status`: active
- `decision`: Fix the local schedule identity model to use a stable `local_id` plus nullable `cloud_schedule_id`, rather than overloading cloud `schedule.id` as the only identity.
- `reason`:
  - Mixed local/cloud records need a stable client identity before cloud creation and after later reconciliation.
  - Reusing the cloud numeric ID as the local primary key would create avoidable churn in sync, markers, and share eligibility logic.
- `impact`:
  - The local repository must store `local_id`, optional `cloud_schedule_id`, `updated_at`, `is_deleted`, `presence`, and `sync_state`.
  - Mixed schedule mapping must preserve `local_id` even after push assigns a cloud identity.

### D-041

- `status`: active
- `decision`: Share selection is limited to schedules that already have confirmed cloud identity.
- `reason`:
  - The protected share route still operates on cloud schedules.
  - Letting local-only records appear selectable would create confusing product failures and blur the cloud/local boundary.
- `impact`:
  - The visual share selector must exclude local-only records.
  - Product copy must guide the user to `Push` first when a local-only schedule is not yet shareable.

### D-042

- `status`: active
- `decision`: R6 acceptance must explicitly verify refresh/reopen persistence, logged-out editability, and backend-unavailable local CRUD.
- `reason`:
  - "Local-first" is not credible if schedules disappear on refresh, become unusable after logout, or fail whenever the backend is unreachable.
  - These are high-risk demo failures that a cloud-centric acceptance path would miss.
- `impact`:
  - Browser verification now includes refresh/reopen, logout, and backend-unavailable checks before the cloud/share/RAG chain.
  - P31 implementation must prove durable local behavior before later sync and sharing polish.

### D-043

- `status`: active
- `decision`: Web local storage must prefer IndexedDB unless the runtime is confirmed to be native Capacitor.
- `reason`:
  - Simply detecting that Capacitor packages are installed is not enough to conclude the app is running on a native device runtime.
  - The first implementation pass exposed a misleading `SQLite` label in the browser because Preferences was available in the bundle.
- `impact`:
  - Storage backend detection now checks native runtime before selecting the Capacitor adapter.
  - Browser users see `IndexedDB` as the active local schedule backend.

### D-044

- `status`: active
- `decision`: Vant components used by the local-first schedule page must be explicitly registered in `main.ts`.
- `reason`:
  - Playwright browser verification exposed runtime Vue warnings for unresolved `Tabs`, `Tab`, and `Skeleton` components.
  - Silent UI component registration drift is a real product risk because the page may partially render while still carrying runtime warnings.
- `impact`:
  - `Tabs`, `Tab`, and `Skeleton` are now registered globally.
  - Browser walkthroughs now run cleanly across the updated schedule view.

### D-045

- `status`: active
- `decision`: Round 7 must restart from `PLAN`; Round 6 terminal docs are historical input only.
- `reason`:
  - The new requirement changes the meaning of local-first sync, delete safety, and share output rather than extending the already-closed R6 acceptance path.
  - Reusing the R6 active state would hide the new semantic defects behind an already-completed round.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new planned round.
  - Executors must not treat R6 terminal state as the live next step.

### D-046

- `status`: active
- `decision`: Schedule state for this round must split `presence` from `sync_intent`.
- `reason`:
  - A single `pending_push` label is too coarse to describe local-first create, update, delete-cloud, and conflict behavior safely.
  - Delete and pull semantics become ambiguous when location and sync intention are collapsed together.
- `impact`:
  - Active contracts now require `presence` plus `sync_intent`.
  - Execution must update schedule visualization and sync logic without reintroducing a single generic unsynced state.

### D-047

- `status`: active
- `decision`: `mark delete cloud` is a queued local intent, not an immediate cloud delete.
- `reason`:
  - Users need a safe delete flow that does not destroy cloud data before explicit `Push`.
  - The round goal explicitly fixes accidental cloud deletion caused by cloud-first semantics.
- `impact`:
  - Delete UI must offer explicit local-vs-cloud behavior for mixed records.
  - The local repository and push flow must support `pending_delete_cloud`.

### D-048

- `status`: active
- `decision`: After a queued cloud delete succeeds on `Push`, the default behavior is to keep the local record and convert it to `local_only`.
- `reason`:
  - The user explicitly chose this behavior during R7 planning.
  - It preserves local-first semantics while still allowing intentional cloud deletion.
- `impact`:
  - Post-push delete handling must not auto-delete the local record.
  - Product copy and status visualization should make the resulting `local_only` state understandable.

### D-049

- `status`: active
- `decision`: `/api/share/{share_uuid}` remains the backend public read route, but it is not the default user-facing copy target.
- `reason`:
  - Copying a raw API route is not a product-grade sharing outcome.
  - The existing frontend currently lacks a dedicated public preview route, so this round must plan for an additive app-facing preview path.
- `impact`:
  - Share output must separate UUID from preview/open actions.
  - Execution may add a frontend public preview route while preserving the existing backend API contract.

### D-050

- `status`: active
- `decision`: Round 8 must restart from `PLAN`; R7 planning docs are historical input only.
- `reason`:
  - The new requirement does not merely continue the previous planning round; it adds a new storage-strategy contract and parse-to-local landing semantics.
  - Reusing the R7 active state would hide new acceptance and contract requirements behind a partially overlapping plan.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new active planning round.
  - Executors must treat R8 as the live planning context.

### D-051

- `status`: active
- `decision`: Schedule semantics in R8 must be expressed across `presence`, `sync_intent`, and `storage_strategy`.
- `reason`:
  - The product needs to distinguish where a record exists, what sync action is pending, and where the user intends the record to live long term.
  - A single unsynced flag cannot safely encode delete-cloud behavior or parse-created destination choices.
- `impact`:
  - The local record contract now includes `storage_strategy`.
  - Execution must present richer state labels without collapsing back to one generic `待上传`.

### D-052

- `status`: active
- `decision`: Parse confirmation must create a local schedule record first, then apply the selected storage strategy.
- `reason`:
  - AI-generated drafts are not equivalent to persisted cloud schedules.
  - The product must keep local-first semantics even when AI participates in schedule creation.
- `impact`:
  - `ParseView` execution work must stop calling cloud `createSchedule(...)` directly on confirmation.
  - Strategy selection must determine whether the resulting local record stays local or becomes pending cloud sync and later rebuild intent.

### D-053

- `status`: active
- `decision`: Delete interaction in R8 is unified behind one danger entry with contextual actions and second confirmation.
- `reason`:
  - Scattered destructive buttons make local/cloud semantics harder to understand and increase accidental destructive behavior.
  - The round requirement explicitly wants one clear delete entry and action-specific explanation.
- `impact`:
  - Execution must redesign the delete interaction rather than only changing internal flags.
  - Local-only, cloud-delete-keep-local, and delete-both actions need distinct confirmation copy and completion handling.

### D-054

- `status`: active
- `decision`: Round 9 must restart from `PLAN`; R8 terminal docs are historical input only.
- `reason`:
  - The new requirement adds a backend knowledge-base policy contract and share-center UUID entry semantics that R8 did not finalize.
  - Reusing R8 active docs would hide new backend and public-link requirements behind a partially overlapping finished round.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new planning round.
  - Executors must treat R9 as the live context and not continue from R8 terminal state.

### D-055

- `status`: active
- `decision`: `sync_to_cloud` and `sync_to_cloud_and_knowledge` must become a real persisted backend distinction instead of a frontend-only intent.
- `reason`:
  - Current cloud schedules do not yet carry a knowledge-base inclusion flag.
  - Current rebuild-all behavior still scans all non-deleted cloud schedules, which breaks the intended product policy.
- `impact`:
  - Execution must introduce an explicit persisted field such as `allow_rag_indexing` or an equivalent policy object.
  - Schedule CRUD, sync push/pull, sync status, and rebuild-all must all honor that policy.

### D-056

- `status`: active
- `decision`: `GET /api/sync/status` must expose both total cloud schedules and knowledge-base-eligible cloud schedules.
- `reason`:
  - The UI cannot explain policy-aware rebuild behavior if backend status only reports total schedules and indexed chunks.
  - The round requirement explicitly asks the product to show the difference between cloud existence and knowledge-base inclusion.
- `impact`:
  - Status aggregation must add a field such as `knowledge_base_eligible_schedule_count`.
  - Frontend status cards and knowledge-base diagnostics can then explain why some cloud schedules are intentionally excluded.

### D-057

- `status`: active
- `decision`: The share center must support both user-facing public links and UUID-driven in-app lookup.
- `reason`:
  - Some users will copy only the UUID, while others need a ready-to-open public link.
  - Share usability remains incomplete if the app can generate UUIDs but cannot guide users from a UUID back into the public preview flow.
- `impact`:
  - Execution must add a UUID input/open entry in the share center.
  - Displayed and copied share results must separate `share_uuid` from the user-facing public link.

### D-058

- `status`: active
- `decision`: Public share links must be generated from a configurable app base URL or the current origin, never from the backend API path.
- `reason`:
  - Copying `/api/share/{uuid}` is not a product-facing result.
  - Multi-environment deployment needs a stable link-generation rule that does not hardcode localhost.
- `impact`:
  - Execution must formalize a public-link generation helper using `VITE_PUBLIC_APP_BASE_URL` when available and current origin otherwise.
  - Share copy/open actions must use that helper consistently.

### D-059

- `status`: active
- `decision`: The persisted backend field name for knowledge-base schedule eligibility is `allow_rag_indexing`.
- `reason`:
  - The planning round allowed the name to vary, but the implementation now needs one stable contract shared by schedule CRUD, sync, rebuild, retrieve, and status aggregation.
  - The field must be explicit enough that `sync_to_cloud` and `sync_to_cloud_and_knowledge` remain visibly different after Push/Pull.
- `impact`:
  - `Schedule`, schedule schemas, sync schemas, sync service, and RAG service all carry `allow_rag_indexing`.
  - `GET /api/sync/status` can now report both total cloud schedules and knowledge-base-eligible schedules.

### D-060

- `status`: active
- `decision`: Rebuild-all deletes and recreates user chunks only for schedules that currently allow RAG indexing.
- `reason`:
  - If a schedule loses knowledge-base eligibility, stale chunks must not remain queryable.
  - Filtering retrieval alone is not enough; rebuild must also converge stored vector state onto the current policy.
- `impact`:
  - `rebuild-all` now clears existing user chunks before recreating chunks for eligible schedules only.
  - Retrieval and indexed counts stay aligned with the current cloud policy.

### D-061

- `status`: active
- `decision`: Round 10 must restart from `PLAN`; R9 terminal docs are historical input only.
- `reason`:
  - The new requirement changes the parse interaction model, temporal contract, and nullable schedule-time semantics instead of merely extending the R9 execution state.
  - Reusing R9 active docs would hide new parse-specific acceptance and contract work behind a finished local-first and share round.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new planning round.
  - Executors must treat R10 as the live context and not continue directly from R9 terminal state.

### D-062

- `status`: active
- `decision`: Parse becomes a single user-visible `智能解析` flow; any stream transport remains an implementation detail.
- `reason`:
  - Users should not choose between overlapping parse modes that do not represent a meaningful product decision.
  - The product goal is one conversational assistant experience, not two adjacent extraction buttons.
- `impact`:
  - Execution must remove the dual-mode parse framing from the page.
  - Backend dual endpoints may remain temporarily for transport purposes, but the UI must expose one primary action only.

### D-063

- `status`: active
- `decision`: `reference_time` is mandatory product input for parse requests and must be sent explicitly by the frontend.
- `reason`:
  - Relative Chinese time phrases are not stable without a known interpretation anchor.
  - The current schema already allows `reference_time`, but the current frontend behavior does not reliably send it.
- `impact`:
  - Execution must thread `reference_time` through parse API calls and use it in parse-service behavior.
  - Missing `reference_time` should be treated as a contract gap to close, not a normal operating mode.

### D-064

- `status`: active
- `decision`: `end_time` becomes nullable across parse, persistence, local storage, and display; the system must not auto-fill a fake precise value.
- `reason`:
  - Many real schedule inputs specify only a start time.
  - The current requirement explicitly rejects hidden defaults like `23:59:59` when the user did not confirm one.
- `impact`:
  - Schedule schemas, local record shape, parse draft shape, validators, and UI formatting all need nullable-end-time support.
  - Missing `end_time` can no longer be treated as an automatic parse-blocking field.

### D-065

- `status`: active
- `decision`: Parse interaction is chat-first, and draft editing must support both AI refinement and manual override with user edits taking precedence.
- `reason`:
  - A conversational assistant plus editable result card matches the product requirement better than a read-only extraction result.
  - Without an explicit precedence rule, later AI updates can silently overwrite user corrections.
- `impact`:
  - Execution must introduce a message-thread model plus an editable draft card.
  - Draft reconciliation logic must preserve manual edits unless the user intentionally changes the field again.

### D-066

- `status`: active
- `decision`: Round 11 must restart from `PLAN`; R10 planned docs are historical input only.
- `reason`:
  - The new requirement changes sync/account semantics and conflict resolution behavior rather than extending the parse-interaction planning round.
  - Reusing the R10 active state would hide account-bound repository and multi-account acceptance work behind an unrelated parse step.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new planning round.
  - Executors must treat R11 as the live planning context and not continue from R10.

### D-067

- `status`: active
- `decision`: Records bound to another cloud account are hidden from the current account's main schedule view.
- `reason`:
  - The user explicitly chose `隐藏` rather than showing other-account-bound records with a special label.
  - This avoids continuing to display stale cloud/synced semantics to the wrong authenticated user while preserving device-local data for the original account context.
- `impact`:
  - Execution must add account-owner metadata to local records and classify them by current-account relevance.
  - Current-account Push/Pull and visible sync labels must ignore hidden other-account-bound records.

### D-068

- `status`: active
- `decision`: R12 prioritizes `Android Capacitor shell + LAN backend connectivity` before Native SQLite formalization.
- `reason`:
  - The current project already has Web-side product loops, but mobile verification is blocked earlier by API addressing, CORS, and missing Capacitor/Android scaffold.
  - Native local storage already uses Capacitor Preferences as a transitional path, so pushing SQLite formalization into this same round would expand risk beyond the minimum mobile-access goal.
- `impact`:
  - This round must make the app shell buildable and LAN-reachable.
  - Docs must explicitly label native Preferences storage as transitional, not final.
  - Native SQLite remains a later round and must not block mobile shell acceptance now.

### D-069

- `status`: active
- `decision`: Round 13 must restart from `PLAN`; R12 active docs are historical input only.
- `reason`:
  - The new requirement changes parse architecture and product semantics rather than extending the mobile-shell execution state.
  - Reusing the R12 active docs would hide the parse-agent contract work behind an unrelated runtime round.
- `impact`:
  - `docs/current_state.md` and `docs/task_board.md` are refreshed as a new planning round.
  - Executors must treat R13 as the live context and not continue from R12 state.

### D-070

- `status`: active
- `decision`: This round's parse flow must be a real sessioned agent workflow with explicit actions/tools, not one-shot parse plus transcript replay.
- `reason`:
  - The current Parse page already looks conversational, which makes it easy to overestimate how much agent behavior already exists.
  - The user's explicit goal is a resume-credible `Parse -> Clarify -> Draft Update -> User Confirm -> Tool Call Save` workflow.
- `impact`:
  - Planning and execution must introduce explicit parse session state, action semantics, and confirm-time save tooling.
  - UI-only chat polish without persistent state progression is not sufficient to close this round.

### D-071

- `status`: active
- `decision`: Parse session state is backend-owned for this round, with the frontend acting as the primary interaction surface.
- `reason`:
  - Backend-owned sessions make it clearer that multi-turn clarification is real workflow state rather than ephemeral client glue.
  - This gives the project a stronger and more explainable `agent application` architecture for demo and resume purposes.
- `impact`:
  - Execution should add explicit session-oriented parse contracts instead of relying on frontend transcript replay alone.
  - Frontend Parse UI still renders and edits draft state, but the authoritative session progression comes from backend session updates.

### D-072

- `status`: active
- `decision`: The admin surface for this round is a Web page inside the existing frontend project, not a second backend app and not a mobile-primary feature.
- `reason`:
  - The product and thesis need a clear user/admin role split, but the current repo already has one backend and one frontend that can host the admin surface.
  - A browser-facing admin page matches the management use case better than forcing admin operations into the mobile primary flow.
- `impact`:
  - Execution adds an admin route/page to the current frontend.
  - Mobile-first ordinary user navigation remains focused on schedules, parse, knowledge base, and share.

### D-073

- `status`: active
- `decision`: Reuse the existing `/api/admin/users` and `/api/admin/users/{user_id}` routes as the only admin data contract for this round.
- `reason`:
  - Backend admin permissions and user-management operations already exist and are covered by tests.
  - Reusing the existing contract avoids inventing a redundant admin API and keeps cloud deployment coordination simple.
- `impact`:
  - This round is primarily a frontend/admin-surface implementation.
  - Cloud deployment only needs to pull the updated frontend/backend mainline without reconciling a second admin service.

### D-074

- `status`: active
- `decision`: Round 17 must restart from `PLAN`; R16 active docs are historical input only.
- `reason`:
  - The new requirement changes backend AI architecture and service-layer execution semantics rather than continuing the completed desktop-polish round.
  - Reusing the R16 active state would incorrectly preserve a frontend-only contract and hide the new LangChain and async acceptance criteria.
- `impact`:
  - `docs/working_contract.md`, `docs/current_state.md`, `docs/task_board.md`, and `docs/api_contract.md` are refreshed as a new active round.
  - Executors must treat R17 as the live planning context and not continue from R16 state.

### D-075

- `status`: active
- `decision`: LangChain will be introduced as a shared orchestration layer for Parse and RAG while retaining the current pgvector retrieval base and draft-confirm persistence rules.
- `reason`:
  - The thesis claim requires real LangChain-backed AI orchestration, but the existing product already has working pgvector retrieval and Parse confirmation semantics that should not be discarded.
  - Replacing the whole retrieval stack would add risk without being necessary to satisfy the round goal.
- `impact`:
  - Parse and RAG execution should converge on shared LangChain-capable runtime seams.
  - Retrieval SQL and schedule confirmation rules remain compatibility anchors during the refactor.

### D-076

- `status`: active
- `decision`: AI paths may use short-lived database session scopes that differ from ordinary CRUD request handling, but the round will not rewrite the whole backend into an async-DB architecture.
- `reason`:
  - The key requirement is to avoid long external model waits holding transactional resources, not to perform a full persistence-layer rewrite.
  - Ordinary CRUD, sync, share, and admin paths are already working and should remain low-risk.
- `impact`:
  - Execution may introduce AI-specific session helpers or route patterns for read -> external await -> write separation.
  - Ordinary business routes remain structurally stable unless a small compatibility fix is strictly required.

### D-077

- `status`: active
- `decision`: Round 17 closes only if both Parse and RAG land on real LangChain-backed core chains.
- `reason`:
  - The thesis claim is about the AI service module rather than a single isolated endpoint.
  - Completing only one chain would still leave the repo unable to support the stronger architecture statement with confidence.
- `impact`:
  - Parse-only or RAG-only LangChain integration is not sufficient for acceptance.
  - Verification and review must demand evidence from both chains.

### D-078

- `status`: active
- `decision`: AI routes must not keep dependency-injected request-scoped database sessions alive while awaiting external model work.
- `reason`:
  - Async model calls only help the architecture claim if the code also stops tying up DB resources during long waits.
  - The current `get_db` pattern is acceptable for ordinary business routes but weakens the AI isolation argument if reused unchanged across awaited external calls.
- `impact`:
  - Execution may move AI-path DB reads and writes into service-owned short sessions.
  - Review should inspect route and service boundaries, not only coroutine signatures.

### D-079

- `status`: active
- `decision`: Round 17 closes at a verified local checkpoint; GitHub synchronization and cloud deployment are intentionally deferred.
- `reason`:
  - The user explicitly required local development, local testing, and local build verification before any GitHub-mediated or cloud-agent deployment step.
  - Keeping deployment out of this round avoids mainline / cloud drift while the LangChain + async AI refactor is still being validated.
- `impact`:
  - Round-close evidence is local backend regression plus local frontend build.
  - A future round may start from this terminal checkpoint to handle GitHub push, cloud deployment, and online verification.
