import { defineStore } from "pinia";
import { ref } from "vue";

import type {
  ParseAgentMessage,
  ParseAgentToolCall,
  ParseSessionResponse
} from "@/api/parse";
import type { ScheduleStorageStrategy } from "@/repositories/local-schedules";

// ---- Types mirroring ParseView component-local state ----

export type DraftFieldKey = "title" | "start_time" | "end_time" | "location" | "remark";

export type DraftFormState = {
  title: string;
  start_time: string;
  end_time: string;
  location: string;
  remark: string;
  storage_strategy: ScheduleStorageStrategy;
};

// ---- Initial / default values ----

const INTRO_MESSAGE: ParseAgentMessage = {
  id: "parse-agent-intro",
  role: "assistant",
  content:
    "先告诉我你的安排，我会把它整理成一张持续更新的日程草稿；缺什么我会继续追问，确认后你再决定如何保存。"
};

function defaultManualEdits(): Record<DraftFieldKey, boolean> {
  return {
    title: false,
    start_time: false,
    end_time: false,
    location: false,
    remark: false
  };
}

function introMessages(): ParseAgentMessage[] {
  return [{ ...INTRO_MESSAGE }];
}

// ---- Store ----

export const useParseSessionStore = defineStore("parse-session", () => {
  // Core session state
  const sessionId = ref<string | null>(null);
  const sessionState = ref<ParseSessionResponse | null>(null);
  const displayedMessages = ref<ParseAgentMessage[]>(introMessages());
  const localToolCalls = ref<ParseAgentToolCall[]>([]);
  const draftForm = ref<DraftFormState | null>(null);
  const manualEdits = ref<Record<DraftFieldKey, boolean>>(defaultManualEdits());
  const composerText = ref("");

  // --- Derived flag: does the store contain an active session? ---
  function hasActiveSession(): boolean {
    return (
      sessionId.value !== null ||
      displayedMessages.value.length > 1 ||
      draftForm.value !== null ||
      composerText.value.trim().length > 0
    );
  }

  // --- Actions ---

  function resetSession(options?: { preserveComposerText?: boolean }) {
    const nextComposerText = options?.preserveComposerText ? composerText.value : "";
    sessionId.value = null;
    sessionState.value = null;
    displayedMessages.value = introMessages();
    localToolCalls.value = [];
    draftForm.value = null;
    manualEdits.value = defaultManualEdits();
    composerText.value = nextComposerText;
  }

  function resetManualEditsOnly() {
    manualEdits.value = defaultManualEdits();
  }

  return {
    // State
    sessionId,
    sessionState,
    displayedMessages,
    localToolCalls,
    draftForm,
    manualEdits,
    composerText,

    // Helpers
    hasActiveSession,

    // Actions
    resetSession,
    resetManualEditsOnly
  };
});
