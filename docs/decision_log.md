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
