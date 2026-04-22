import { api } from "@/api/client";
import type { ScheduleStorageStrategy } from "@/repositories/local-schedules";

const PARSE_REQUEST_TIMEOUT_MS = 45_000;

export type ParseScheduleDraft = {
  title: string | null;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  remark: string | null;
  source: "ai_parsed";
  storage_strategy: ScheduleStorageStrategy | null;
};

export type ParseAgentMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type ParseAgentTraceEntry = {
  action:
    | "build_context"
    | "plan_update"
    | "apply_draft_update"
    | "request_clarification"
    | "prepare_confirmation";
  summary: string;
  source?: "runtime" | "heuristic" | "manual_patch" | null;
};

export type ParseAgentToolCall = {
  name: "update_draft" | "ask_follow_up" | "finalize_draft" | "save_schedule_to_local";
  summary: string;
};

export type ParseDraftResponse = {
  draft: ParseScheduleDraft;
  missing_fields: string[];
  follow_up_questions: Array<{ field: string; question: string }>;
  state: "clarifying" | "ready_for_confirm";
  trace: ParseAgentTraceEntry[];
  requires_human_review: boolean;
  can_persist_directly: boolean;
};

export type ParseSessionResponse = {
  parse_session_id: string;
  messages: ParseAgentMessage[];
  draft: ParseScheduleDraft;
  missing_fields: string[];
  follow_up_questions: Array<{ field: string; question: string }>;
  state: "clarifying" | "ready_for_confirm";
  ready_for_confirm: boolean;
  next_action: "ask_follow_up" | "finalize_draft";
  tool_calls: ParseAgentToolCall[];
  trace: ParseAgentTraceEntry[];
  latest_assistant_message: string | null;
  draft_visible: boolean;
};

export type ParseSessionCreateRequest = {
  message: string;
  reference_time: string;
};

export type ParseSessionMessageRequest = {
  message: string;
  reference_time: string;
};

export type ParseSessionDraftPatchRequest = {
  draft: {
    title?: string | null;
    start_time?: string | null;
    end_time?: string | null;
    location?: string | null;
    remark?: string | null;
    storage_strategy?: ScheduleStorageStrategy | null;
  };
};

export async function createParseSession(payload: ParseSessionCreateRequest): Promise<ParseSessionResponse> {
  const response = await api.post<ParseSessionResponse>("/parse/sessions", payload, {
    timeout: PARSE_REQUEST_TIMEOUT_MS
  });
  return response.data;
}

export async function continueParseSession(
  sessionId: string,
  payload: ParseSessionMessageRequest
): Promise<ParseSessionResponse> {
  const response = await api.post<ParseSessionResponse>(`/parse/sessions/${sessionId}/messages`, payload, {
    timeout: PARSE_REQUEST_TIMEOUT_MS
  });
  return response.data;
}

export async function patchParseSessionDraft(
  sessionId: string,
  payload: ParseSessionDraftPatchRequest
): Promise<ParseSessionResponse> {
  const response = await api.patch<ParseSessionResponse>(`/parse/sessions/${sessionId}/draft`, payload, {
    timeout: PARSE_REQUEST_TIMEOUT_MS
  });
  return response.data;
}
