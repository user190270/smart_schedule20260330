<template>
  <div class="parse-container">
    <section class="hero-block">
      <h2 class="view-title">智能解析</h2>
      <p class="view-subtitle">用自然语言描述你的安排</p>
    </section>

    <section class="panel chat-panel">
      <div class="panel-header">
        <van-icon name="chat-o" color="var(--color-primary)" size="20" />
        <h3 class="panel-title">解析会话</h3>
        <div class="spacer"></div>
        <van-button
          plain
          round
          type="primary"
          size="small"
          icon="plus"
          :disabled="loading || saving"
          @click="startNewSession()"
        >
          新会话
        </van-button>
      </div>

      <div class="sample-row">
        <button
          v-for="sample in quickSamples"
          :key="sample"
          type="button"
          class="sample-chip"
          @click="composerText = sample"
        >
          {{ sample }}
        </button>
      </div>

      <div class="session-summary">
        <div class="summary-card">
          <span class="summary-label">当前阶段</span>
          <strong>{{ sessionStageLabel }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">参考时间</span>
          <strong>{{ referenceTimeLabel }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">缺失字段</span>
          <strong>{{ missingFieldsLabel }}</strong>
        </div>
      </div>

      <div class="message-list">
        <article
          v-for="message in displayedMessages"
          :key="message.id"
          class="message-card"
          :class="message.role === 'user' ? 'message-user' : 'message-assistant'"
        >
          <div class="message-meta">{{ message.role === "user" ? "你" : "解析 Agent" }}</div>
          <div class="message-content">{{ message.content }}</div>
        </article>
      </div>

      <div v-if="displayedTraceEntries.length > 0" class="tool-trace">
        <div class="tool-trace-title">最近轨迹</div>
        <div class="tool-trace-list">
          <div v-for="(entry, index) in displayedTraceEntries" :key="`${entry.action}-${index}`" class="tool-pill">
            <strong>{{ traceActionLabel(entry.action) }}</strong>
            <span>{{ entry.summary }}</span>
            <small v-if="entry.source" class="tool-source">{{ traceSourceLabel(entry.source) }}</small>
          </div>
        </div>
      </div>

      <div class="composer-panel">
        <van-field
          v-model="composerText"
          type="textarea"
          rows="4"
          autosize
          placeholder="例如：明早8点到9点在三饭吃饭"
          class="composer-field"
        />
        <div class="composer-footer">
          <span class="reference-time">参考时间：{{ referenceTimeLabel }}</span>
          <van-button type="primary" round icon="chat-o" :loading="loading" @click="submitMessage">
            智能解析
          </van-button>
        </div>
      </div>
    </section>

    <section v-if="showDraftCard && draftForm" class="panel draft-panel">
      <div class="panel-header">
        <van-icon name="edit" color="var(--color-primary)" size="20" />
        <h3 class="panel-title">日程草稿确认卡</h3>
      </div>

      <div class="draft-status">
        <van-tag round plain :type="readyForConfirm ? 'success' : 'warning'">
          {{ readyForConfirm ? "可确认保存" : "继续澄清中" }}
        </van-tag>
        <van-tag round plain type="primary">
          {{ nextActionLabel }}
        </van-tag>
      </div>

      <van-form @submit="persistDraft" class="draft-form">
        <van-field
          v-model="draftForm.title"
          label-align="top"
          label="标题"
          placeholder="例如：开会、吃饭、复盘"
          @update:model-value="handleDraftFieldEdit('title')"
        />

        <div class="datetime-grid">
          <van-field
            v-model="draftForm.start_time"
            type="datetime-local"
            label-align="top"
            label="开始时间"
            placeholder="请选择开始时间"
            @update:model-value="handleDraftFieldEdit('start_time')"
          />
          <van-field
            v-model="draftForm.end_time"
            type="datetime-local"
            label-align="top"
            label="结束时间"
            placeholder="可选，不填也能保存"
            @update:model-value="handleDraftFieldEdit('end_time')"
          />
        </div>

        <div class="time-preview-grid">
          <div class="time-preview-card">
            <span class="time-preview-label">开始时间预览</span>
            <strong>{{ formatDraftDateTime(draftForm.start_time, "未设置开始时间") }}</strong>
          </div>
          <div class="time-preview-card">
            <span class="time-preview-label">结束时间预览</span>
            <strong>{{ formatDraftDateTime(draftForm.end_time, "未设置结束时间") }}</strong>
          </div>
        </div>

        <div class="quick-end-actions">
          <button type="button" class="quick-end-chip" @click="applyQuickEndTime(30)">+30 分钟</button>
          <button type="button" class="quick-end-chip" @click="applyQuickEndTime(60)">+1 小时</button>
          <button type="button" class="quick-end-chip" @click="clearEndTime">不设置结束时间</button>
        </div>

        <van-field
          v-model="draftForm.location"
          label-align="top"
          label="地点"
          placeholder="例如：A-201、图书馆 2 楼、三饭"
          @update:model-value="handleDraftFieldEdit('location')"
        />
        <van-field
          v-model="draftForm.remark"
          type="textarea"
          rows="3"
          autosize
          label-align="top"
          label="备注"
          placeholder="补充上下文、参与人或提醒信息"
          @update:model-value="handleDraftFieldEdit('remark')"
        />

        <div class="strategy-section">
          <div class="strategy-title">保存策略</div>
          <div class="strategy-options">
            <button
              v-for="option in strategyOptions"
              :key="option.value"
              type="button"
              class="strategy-option"
              :class="{ active: draftForm.storage_strategy === option.value }"
              @click="selectStrategy(option.value)"
            >
              <strong>{{ option.label }}</strong>
              <span>{{ option.hint }}</span>
            </button>
          </div>
        </div>

        <div class="persist-panel">

          <van-button
            type="primary"
            round
            block
            native-type="submit"
            :loading="saving"
            :disabled="!canPersistDraft"
          >
            确认并保存到本地仓
          </van-button>
        </div>
      </van-form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { showNotify } from "vant";

import {
  continueParseSession,
  createParseSession,
  patchParseSessionDraft,
  type ParseAgentMessage,
  type ParseAgentToolCall,
  type ParseAgentTraceEntry,
  type ParseScheduleDraft,
  type ParseSessionResponse
} from "@/api/parse";
import type { ScheduleStorageStrategy } from "@/repositories/local-schedules";
import { useAuthStore } from "@/stores/auth";
import { useLocalScheduleStore } from "@/stores/local-schedules";
import { useParseSessionStore, type DraftFieldKey, type DraftFormState } from "@/stores/parse-session";
import {
  formatScheduleDateTime,
  fromDatetimeLocalValue,
  toDatetimeLocalValue,
  toOffsetIsoString
} from "@/utils/schedule-time";
import { extractApiErrorMessage } from "@/services/api-errors";

const router = useRouter();
const authStore = useAuthStore();
const localScheduleStore = useLocalScheduleStore();
const parseSessionStore = useParseSessionStore();

const loading = ref(false);
const saving = ref(false);

const {
  sessionId,
  sessionState,
  displayedMessages,
  localToolCalls,
  draftForm,
  manualEdits,
  composerText
} = storeToRefs(parseSessionStore);

const quickSamples = [
  "明早8点到9点在三饭吃饭",
  "明天到 A-201 开会",
  "下周三下午和 Alice 在图书馆讨论 RAG 方案"
];

const strategyOptions = computed(() => localScheduleStore.storageStrategyOptions());
const readyForConfirm = computed(() => sessionState.value?.state === "ready_for_confirm");
const nextActionLabel = computed(() =>
  sessionState.value?.next_action === "finalize_draft" ? "下一步：确认草稿" : "下一步：继续澄清"
);
const showDraftCard = computed(() => sessionState.value?.draft_visible ?? false);
const missingFieldsLabel = computed(() => {
  const fields = sessionState.value?.missing_fields ?? [];
  if (fields.length === 0) {
    return "无";
  }
  return fields.map(mapMissingFieldLabel).join("、");
});
const sessionStageLabel = computed(() => {
  if (!sessionState.value) {
    return "等待开始";
  }
  return sessionState.value.state === "ready_for_confirm" ? "待确认" : "澄清中";
});
type DisplayedTraceEntry = {
  action: string;
  summary: string;
  source?: ParseAgentTraceEntry["source"];
};

const displayedTraceEntries = computed<DisplayedTraceEntry[]>(() => {
  const responseTrace = sessionState.value?.trace ?? [];
  const legacyTrace =
    responseTrace.length > 0
      ? responseTrace
      : (sessionState.value?.tool_calls ?? []).map((tool) => ({
          action: tool.name,
          summary: tool.summary,
          source: null
        }));

  return [...legacyTrace, ...localToolCalls.value.map((tool) => ({ action: tool.name, summary: tool.summary, source: null }))].slice(-4);
});
const referenceTimeLabel = computed(() => formatScheduleDateTime(buildReferenceTime()));
const canPersistDraft = computed(() => {
  if (!draftForm.value) {
    return false;
  }
  return draftForm.value.title.trim().length > 0 && draftForm.value.start_time.trim().length > 0;
});

let draftSyncTimer: ReturnType<typeof setTimeout> | null = null;
let draftSyncPromise: Promise<void> | null = null;

onMounted(async () => {
  await authStore.hydrate();
  await localScheduleStore.initialize();
});

onBeforeUnmount(() => {
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer);
    draftSyncTimer = null;
  }
});

function defaultStorageStrategy(): ScheduleStorageStrategy {
  return authStore.isAuthenticated ? "sync_to_cloud" : "local_only";
}

function createDraftFormState(): DraftFormState {
  return {
    title: "",
    start_time: "",
    end_time: "",
    location: "",
    remark: "",
    storage_strategy: defaultStorageStrategy()
  };
}

function resetManualEdits() {
  parseSessionStore.resetManualEditsOnly();
}

function mapMissingFieldLabel(field: string): string {
  switch (field) {
    case "title":
      return "标题";
    case "start_time":
      return "开始时间";
    default:
      return field;
  }
}

function traceActionLabel(action: string): string {
  switch (action) {
    case "build_context":
      return "构建上下文";
    case "plan_update":
      return "生成计划";
    case "apply_draft_update":
      return "应用草稿更新";
    case "request_clarification":
      return "请求澄清";
    case "prepare_confirmation":
      return "准备确认";
    case "update_draft":
      return "更新草稿";
    case "ask_follow_up":
      return "继续澄清";
    case "finalize_draft":
      return "确认草稿";
    case "save_schedule_to_local":
      return "保存到本地仓";
    default:
      return action;
  }
}

function traceSourceLabel(source: ParseAgentTraceEntry["source"]): string {
  switch (source) {
    case "runtime":
      return "runtime";
    case "heuristic":
      return "heuristic";
    case "manual_patch":
      return "manual_patch";
    default:
      return "";
  }
}

function buildReferenceTime(): string {
  return toOffsetIsoString(new Date());
}

function formatError(error: unknown, fallback: string): string {
  return extractApiErrorMessage(error, fallback);
}

function mergeDraftFromSession(draft: ParseScheduleDraft, preserveManualFields = true) {
  const nextForm = draftForm.value ? { ...draftForm.value } : createDraftFormState();
  const incoming: Record<DraftFieldKey, string> = {
    title: draft.title ?? "",
    start_time: toDatetimeLocalValue(draft.start_time),
    end_time: toDatetimeLocalValue(draft.end_time),
    location: draft.location ?? "",
    remark: draft.remark ?? ""
  };

  (Object.keys(incoming) as DraftFieldKey[]).forEach((field) => {
    if (preserveManualFields && manualEdits.value[field]) {
      return;
    }
    nextForm[field] = incoming[field];
  });

  nextForm.storage_strategy = draft.storage_strategy ?? nextForm.storage_strategy ?? defaultStorageStrategy();
  draftForm.value = nextForm;
}

function applySessionResponse(response: ParseSessionResponse, preserveManualFields = true) {
  sessionId.value = response.parse_session_id;
  sessionState.value = response;
  displayedMessages.value = response.messages;
  if (response.draft_visible) {
    mergeDraftFromSession(response.draft, preserveManualFields);
  }
}

function cancelDraftSync() {
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer);
    draftSyncTimer = null;
  }
  draftSyncPromise = null;
}

function startNewSession(options?: { preserveComposerText?: boolean }) {
  cancelDraftSync();
  parseSessionStore.resetSession(options);
}

function serializeDraftPatch() {
  if (!draftForm.value) {
    return null;
  }

  return {
    title: draftForm.value.title.trim() || null,
    start_time: fromDatetimeLocalValue(draftForm.value.start_time),
    end_time: fromDatetimeLocalValue(draftForm.value.end_time),
    location: draftForm.value.location.trim() || null,
    remark: draftForm.value.remark.trim() || null,
    storage_strategy: draftForm.value.storage_strategy
  };
}

async function syncDraftPatch(silent = true) {
  if (!sessionId.value) {
    return;
  }
  const payload = serializeDraftPatch();
  if (!payload) {
    return;
  }

  try {
    const response = await patchParseSessionDraft(sessionId.value, { draft: payload });
    applySessionResponse(response, true);
  } catch (error) {
    if (!silent) {
      throw error;
    }
  }
}

function queueDraftSync() {
  if (!sessionId.value || !draftForm.value) {
    return;
  }
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer);
  }
  draftSyncPromise = new Promise((resolve) => {
    draftSyncTimer = setTimeout(async () => {
      draftSyncTimer = null;
      try {
        await syncDraftPatch(true);
      } finally {
        resolve();
        draftSyncPromise = null;
      }
    }, 500);
  });
}

async function flushDraftSync() {
  if (draftSyncTimer) {
    clearTimeout(draftSyncTimer);
    draftSyncTimer = null;
    await syncDraftPatch(false);
    draftSyncPromise = null;
    return;
  }
  if (draftSyncPromise) {
    await draftSyncPromise;
  }
}

function handleDraftFieldEdit(field: DraftFieldKey) {
  manualEdits.value[field] = true;
  queueDraftSync();
}

function selectStrategy(strategy: ScheduleStorageStrategy) {
  if (!draftForm.value) {
    return;
  }
  draftForm.value.storage_strategy = strategy;
  queueDraftSync();
}

function formatDraftDateTime(inputValue: string, emptyLabel: string): string {
  const isoValue = fromDatetimeLocalValue(inputValue);
  if (!isoValue) {
    return emptyLabel;
  }
  return formatScheduleDateTime(isoValue);
}

function applyQuickEndTime(minutes: number) {
  if (!draftForm.value) {
    return;
  }
  const startIso = fromDatetimeLocalValue(draftForm.value.start_time);
  if (!startIso) {
    showNotify({ type: "warning", message: "请先设置开始时间，再使用快捷结束时间。" });
    return;
  }

  const endDate = new Date(startIso);
  endDate.setMinutes(endDate.getMinutes() + minutes);
  draftForm.value.end_time = toDatetimeLocalValue(endDate.toISOString());
  handleDraftFieldEdit("end_time");
}

function clearEndTime() {
  if (!draftForm.value) {
    return;
  }
  draftForm.value.end_time = "";
  handleDraftFieldEdit("end_time");
}

async function submitMessage() {
  const message = composerText.value.trim();
  if (!message) {
    showNotify({ type: "warning", message: "请先输入你想让 Agent 解析的日程描述。" });
    return;
  }
  if (!authStore.isAuthenticated) {
    showNotify({ type: "warning", message: "智能解析目前依赖云端 AI，请先登录后再使用。" });
    return;
  }

  loading.value = true;
  try {
    await flushDraftSync();
    const referenceTime = buildReferenceTime();
    const response = sessionId.value
      ? await continueParseSession(sessionId.value, { message, reference_time: referenceTime })
      : await createParseSession({ message, reference_time: referenceTime });

    if (!sessionId.value) {
      resetManualEdits();
      localToolCalls.value = [];
    }

    applySessionResponse(response, true);
    composerText.value = "";
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "智能解析失败，请稍后重试。") });
  } finally {
    loading.value = false;
  }
}

async function persistDraft() {
  if (!draftForm.value) {
    return;
  }

  const title = draftForm.value.title.trim();
  const startTime = fromDatetimeLocalValue(draftForm.value.start_time);
  const endTime = fromDatetimeLocalValue(draftForm.value.end_time);

  if (!title || !startTime) {
    showNotify({ type: "warning", message: "标题和开始时间是最少必填项。请先补全再保存。" });
    return;
  }

  saving.value = true;
  try {
    await flushDraftSync();
    await localScheduleStore.createSchedule({
      title,
      start_time: startTime,
      end_time: endTime,
      location: draftForm.value.location.trim() || null,
      remark: draftForm.value.remark.trim() || null,
      source: "ai_parsed",
      storage_strategy: draftForm.value.storage_strategy
    });

    const saveToolCall: ParseAgentToolCall = {
      name: "save_schedule_to_local",
      summary: "已调用本地保存工具，把确认后的草稿写入本地仓。"
    };
    localToolCalls.value = [...localToolCalls.value, saveToolCall].slice(-4);

    showNotify({
      type: "success",
      message:
        draftForm.value.storage_strategy === "local_only"
          ? "草稿已保存到本地仓。"
          : "草稿已保存到本地仓；后续可通过 Push / Rebuild 进入云端与知识库。"
    });

    startNewSession();
    await router.push("/schedules");
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "保存草稿失败，请稍后重试。") });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.parse-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.hero-block {
  padding: 0 var(--spacing-xs);
}

.view-title {
  margin: 0 0 var(--spacing-xs);
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-main);
}

.view-subtitle {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.panel-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.spacer {
  flex: 1;
}

.sample-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.sample-chip,
.quick-end-chip {
  border: 1px solid var(--bg-subtle);
  border-radius: 999px;
  background: var(--bg-surface);
  padding: 8px 12px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.session-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.summary-card {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-app);
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-label {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.message-card {
  max-width: 88%;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--bg-subtle);
  white-space: pre-wrap;
  line-height: 1.7;
}

.message-assistant {
  align-self: flex-start;
  background: #f8fbff;
}

.message-user {
  align-self: flex-end;
  background: #eef6ff;
}

.message-meta {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-bottom: 6px;
}

.message-content {
  color: var(--text-main);
}

.tool-trace {
  border: 1px dashed var(--bg-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.tool-trace-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: var(--spacing-sm);
}

.tool-trace-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.tool-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--bg-app);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
}

.tool-pill strong {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.tool-pill span {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.tool-source {
  font-size: 11px;
  color: var(--text-muted);
}

.composer-panel {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  padding: var(--spacing-sm);
}

.composer-field {
  background: transparent;
}

.composer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  flex-wrap: wrap;
}

.reference-time {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.draft-status {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-md);
}

.draft-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.datetime-grid,
.time-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.time-preview-card {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  background: var(--bg-app);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.time-preview-label {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.quick-end-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.strategy-section {
  margin-top: var(--spacing-sm);
}

.strategy-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: var(--spacing-sm);
}

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.strategy-option {
  width: 100%;
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  padding: var(--spacing-md);
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.strategy-option.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.strategy-option strong {
  color: var(--text-main);
  font-size: var(--font-size-sm);
}

.strategy-option span,
.persist-hint {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.7;
}

.persist-panel {
  margin-top: var(--spacing-sm);
}

@media (max-width: 640px) {
  .session-summary,
  .datetime-grid,
  .time-preview-grid {
    grid-template-columns: 1fr;
  }

  .message-card {
    max-width: 100%;
  }
}
</style>
