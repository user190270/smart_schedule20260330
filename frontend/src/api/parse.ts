import { api } from "@/api/client";
import type { ScheduleStorageStrategy } from "@/repositories/local-schedules";

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

export type ParseAgentToolCall = {
  name: "update_draft" | "ask_follow_up" | "finalize_draft" | "save_schedule_to_local";
  summary: string;
};

export type ParseSessionResponse = {
  parse_session_id: string;
  messages: ParseAgentMessage[];
  draft: ParseScheduleDraft;
  missing_fields: string[];
  follow_up_questions: Array<{ field: string; question: string }>;
  ready_for_confirm: boolean;
  next_action: "ask_follow_up" | "finalize_draft";
  tool_calls: ParseAgentToolCall[];
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
  const response = await api.post<ParseSessionResponse>("/parse/sessions", payload);
  return response.data;
}

export async function continueParseSession(
  sessionId: string,
  payload: ParseSessionMessageRequest
): Promise<ParseSessionResponse> {
  const response = await api.post<ParseSessionResponse>(`/parse/sessions/${sessionId}/messages`, payload);
  return response.data;
}

export async function patchParseSessionDraft(
  sessionId: string,
  payload: ParseSessionDraftPatchRequest
): Promise<ParseSessionResponse> {
  const response = await api.patch<ParseSessionResponse>(`/parse/sessions/${sessionId}/draft`, payload);
  return response.data;
}
