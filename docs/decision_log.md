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

### D-080

- `status`: active
- `decision`: Round 18 must restart from `PLAN`; R17 terminal docs are historical input only.
- `reason`:
  - The new requirement changes Parse session semantics and referential-update behavior rather than extending the completed LangChain/async round.
- `impact`:
  - `docs/working_contract.md`, `docs/current_state.md`, `docs/task_board.md`, and `docs/api_contract.md` are refreshed as a new active round.
  - Executors must treat R18 as the live planning context and not continue from R17 terminal state.

### D-081

- `status`: active
- `decision`: This round improves Parse by strengthening session context packaging and field-level merge semantics, not by rebuilding Parse into a general chatbot.
- `reason`:
  - The user requirement is about referential multi-turn updates inside the existing draft-first workflow.
  - A chat-general redesign would add risk and blur the product scope.
- `impact`:
  - Execution stays concentrated in Parse service logic, tests, and only minimal supporting seams.
  - Reviewer should reject steps that broaden Parse into a generic conversation system.

### D-082

- `status`: active
- `decision`: Partial-update behavior defaults to preserving unrelated draft fields unless the latest instruction clearly replaces or clears them.
- `reason`:
  - The current product risk is accidental field clobbering during follow-up instructions.
  - Reliable add / replace / keep / clear semantics are the round's core acceptance target.
- `impact`:
  - Execution makes field-intent handling explicit in the Parse path.
  - Tests prove keep-only, replace-only, and clear-only scenarios.

### D-083

- `status`: active
- `decision`: Any Parse frontend or schema adjustment in this round must be additive and delayed until after backend context and merge behavior are stable.
- `reason`:
  - The current frontend already has a usable chat-plus-draft surface.
  - The user explicitly prefers backend semantics first and only minimal UI or contract alignment if truly needed.
- `impact`:
  - Initial execution steps stay backend-first.
  - Frontend changes, if any, must remain minimal and reviewable.

### D-084

- `status`: active
- `decision`: Parse session follow-ups use a field-level update-plan seam plus structured prior-turn context rather than the previous coarse full-draft merge.
- `reason`:
  - Referential instructions need explicit `keep / set / clear` semantics to avoid clobbering unrelated fields.
  - Prior-turn context is necessary for instructions that refer back to earlier turns, but the product still needs to remain a draft-oriented scheduling flow rather than a general chat system.
- `impact`:
  - `server/app/services/parse_service.py` now packages prior user turns and field history for runtime calls.
  - Backend merge behavior is easier to test directly against partial-update scenarios.

### D-085

- `status`: active
- `decision`: Short Parse follow-up answers are handled by strengthening explicit follow-up context and by allowing the existing fallback path to rescue only actively pending fields when the runtime returns `keep`.
- `reason`:
  - The target failure mode is not broad time-expression coverage but under-specified model-facing clarification context.
  - Purely relying on the runtime to reinterpret short replies like `早上九点开始` leaves a gap when the runtime keeps a still-missing field even though the existing fallback path can already extract that value.
- `impact`:
  - `server/app/services/parse_service.py` now sends the latest assistant clarification, current missing fields, current follow-up questions, and recent dialogue cues inside `session_context`.
  - The `keep / set / clear` seam remains intact, but a pending field can now prefer the fallback action over a runtime `keep` when that field is still the active clarification target.

### D-086

- `status`: active
- `decision`: RAG true streaming preserves the existing `meta / token / done` SSE contract while shifting token generation to the runtime streaming iterator and delaying assistant-history persistence until successful completion.
- `reason`:
  - The product already has a working frontend SSE consumer, so event-shape churn would add unnecessary migration risk.
  - The actual implementation gap was backend timing semantics, not route naming.
  - Persisting partial assistant text on a failed stream would make chat history inconsistent with what the user actually received.
- `impact`:
  - `server/app/routers/rag.py` forwards real runtime chunks as `token` events and emits terminal `done` markers.
  - `server/app/services/rag_service.py` accumulates streamed chunks and writes chat history only after successful completion.
  - `frontend/src/views/RagView.vue` appends raw chunk text instead of adding a forced trailing space to each token.

### D-087

- `status`: active
- `decision`: Parse must treat fallback-detected explicit time signals as the boundary for accepting a newly fabricated `start_time`.
- `reason`:
  - The current defect is not missing follow-up support but unsupported model invention, especially defaulting vague future activities to `09:00`.
  - The existing fallback extractor already defines whether the latest message actually contains time evidence.
- `impact`:
  - Parse runtime prompt and post-runtime merge logic must reject unsupported `start_time` inventions.
  - Follow-up answers that genuinely contain time signals remain valid.

### D-088

- `status`: active
- `decision`: RAG temporal grounding will be repaired by enriching indexed schedule source text with structured date/time facts instead of changing route contracts or session semantics.
- `reason`:
  - The current multi-turn RAG issue comes from weak indexed grounding, not from missing streaming or missing `session_history`.
  - A source-text enrichment is the smallest fix that strengthens date-aware answers without a frontend or API redesign.
- `impact`:
  - `_build_schedule_source_text(...)` must emit structured temporal facts.
  - Existing SSE and session-history contracts remain unchanged.

### D-089

- `status`: active
- `decision`: R25 will repair RAG quality by replacing raw fixed-width fragment chunking with schedule-aware chunks and by grouping retrieved evidence at the schedule level before answer generation.
- `reason`:
  - The current RAG issue is no longer just missing fields; retrieval now feeds the model repeated fragment noise that makes time reasoning unstable.
  - Fixing chunking and pre-generation evidence organization is lower risk than changing routes, session semantics, or providers.
- `impact`:
  - `server/app/services/rag_service.py` becomes the main execution surface for chunk construction, local-time formatting, retrieval consolidation, and answer payload shaping.
  - Existing SSE and multi-turn contracts stay intact while answer quality is improved through cleaner context organization.

### D-090

- `status`: active
- `decision`: Optional cloud email reminders will use additive user/schedule fields plus a persisted reminder table and a lightweight in-process background scanner, rather than changing auth requirements or introducing new infrastructure.
- `reason`:
  - The round needs real send scheduling and idempotency, but the user explicitly wants a sidecar capability that does not disturb the existing mainline product flows.
  - There is no existing worker stack in the repo, and inventing one would expand scope more than necessary for a local-only implementation round.
- `impact`:
  - Backend schema changes stay narrowly focused on optional email config, cloud schedule reminder settings, and reminder-send state.
  - Request paths may recompute reminder records, but actual sending happens off the main request path.
  - Frontend work remains limited to the smallest settings surface needed to configure and enable the feature.
