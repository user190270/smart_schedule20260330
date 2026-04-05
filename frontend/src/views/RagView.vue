<template>
  <div class="rag-container">
    <section class="header-section">
      <h2 class="view-title">知识库问答</h2>
      <p class="view-subtitle">基于云端知识库检索与真实流式生成，为日程场景提供可追问的问答体验。</p>
    </section>

    <section class="panel status-panel">
      <div class="panel-header">
        <van-icon name="cluster-o" color="var(--color-primary)" size="20" />
        <h2 class="panel-title">知识库状态</h2>
      </div>

      <div class="status-grid">
        <div class="status-card">
          <span class="status-label">云端日程数</span>
          <strong class="status-value">{{ syncStore.status?.cloud_schedule_count ?? 0 }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">可入知识库日程</span>
          <strong class="status-value">{{ syncStore.status?.knowledge_base_eligible_schedule_count ?? 0 }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">已索引日程数</span>
          <strong class="status-value">{{ syncStore.status?.indexed_schedule_count ?? 0 }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">已索引 Chunks</span>
          <strong class="status-value">{{ syncStore.status?.indexed_chunk_count ?? 0 }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">最近重建时间</span>
          <strong class="status-value">{{ formatTime(syncStore.status?.last_knowledge_rebuild_at ?? null) }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">最近重建状态</span>
          <strong class="status-value">{{ rebuildStatusLabel }}</strong>
        </div>
      </div>

      <div class="status-actions">
        <van-button type="success" round :disabled="!authStore.isAuthenticated" @click="runRebuild">
          Rebuild Knowledge Base
        </van-button>
        <van-button round :disabled="!authStore.isAuthenticated" @click="refreshStatus">刷新状态</van-button>
      </div>

      <div class="diagnostic-box" :class="diagnosticToneClass">
        <div class="diagnostic-title">当前建议：{{ diagnostic.key }}</div>
        <div class="diagnostic-message">{{ diagnostic.message }}</div>
      </div>
    </section>

    <div class="rag-main-content">
      <section class="panel query-panel">
        <van-field
          v-model="question"
          label-align="top"
          label="问题"
          placeholder="例如：我明天第一个安排是什么？然后继续追问“地点呢”或“那下一个是几点？”"
          class="custom-field"
        />

        <div class="action-buttons">
          <van-button type="primary" round icon="search" :loading="loadingRetrieve" @click="runRetrieve">仅检索</van-button>
          <van-button type="success" round icon="chat-o" plain :loading="loadingStream" @click="runStream">AI 问答</van-button>
          <van-button round plain :disabled="loadingStream || !sessionTurns.length" @click="startNewSession">新会话</van-button>
        </div>
      </section>

      <section class="panel session-panel" v-if="historyTurns.length > 0">
        <div class="panel-header">
          <van-icon name="comment-o" color="var(--color-primary)" size="20" />
          <h2 class="panel-title">本轮问答历史</h2>
        </div>

        <div class="session-turn-list">
          <article v-for="turn in historyTurns" :key="turn.id" class="session-turn-card">
            <div class="session-turn-question">{{ turn.question }}</div>
            <div class="session-turn-answer">{{ turn.answer }}</div>
            <div class="session-turn-meta">检索上下文：{{ turn.retrievedChunks }} 条</div>
          </article>
        </div>
      </section>

      <transition name="fade">
        <section class="panel answer-panel" v-if="answerText || loadingStream">
          <div class="panel-header">
            <van-icon name="bulb-o" color="var(--color-primary)" size="20" />
            <h2 class="panel-title">当前回答</h2>
          </div>

          <div class="answer-content">
            <p v-if="loadingStream && !answerText" class="loading-text">AI 正在流式生成回答...</p>
            <div v-else class="markdown-body">{{ answerText }}</div>
          </div>

          <div class="meta-footer" v-if="metaInfo !== '-'">
            <span class="meta-text"><van-icon name="info-o" /> {{ metaInfo }}</span>
          </div>
        </section>
      </transition>

      <section class="panel context-panel" v-if="retrieved.length > 0">
        <div class="panel-header">
          <van-icon name="description" color="var(--text-secondary)" size="18" />
          <h2 class="panel-title">检索命中的上下文</h2>
        </div>

        <div class="chunk-list">
          <div v-for="(item, idx) in retrieved" :key="item.chunk_id" class="chunk-card">
            <div class="chunk-header">
              <span class="chunk-id">命中 {{ idx + 1 }} / 日程 {{ item.schedule_id }}</span>
              <span class="chunk-score">相关度 {{ (item.score * 100).toFixed(1) }}%</span>
            </div>
            <div class="chunk-content">{{ item.content }}</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { showNotify } from "vant";

import { getAccessToken } from "@/api/client";
import { retrieveRagContext, streamRagAnswer, type RagRetrievedChunk } from "@/api/rag";
import { useAuthStore } from "@/stores/auth";
import { useCloudSyncStore } from "@/stores/cloud-sync";

type DiagnosticState = {
  key: "not_logged_in" | "no_cloud_schedules" | "not_pushed" | "pushed_not_indexed" | "indexed_no_hit" | "ready";
  tone: "warning" | "info" | "success";
  message: string;
};

type RagConversationTurn = {
  id: string;
  question: string;
  answer: string;
  retrievedChunks: number;
  status: "streaming" | "completed" | "failed";
};

const authStore = useAuthStore();
const syncStore = useCloudSyncStore();

const question = ref("");
const loadingRetrieve = ref(false);
const loadingStream = ref(false);
const retrieved = ref<RagRetrievedChunk[]>([]);
const answerText = ref("");
const metaInfo = ref("-");
const lastDiagnosticKey = ref<DiagnosticState["key"]>("ready");
const sessionId = ref<string | null>(null);
const sessionTurns = ref<RagConversationTurn[]>([]);

const rebuildStatusLabel = computed(() => {
  const status = syncStore.status?.last_knowledge_rebuild_status ?? "idle";
  if (status === "success") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  return "尚未重建";
});

const diagnostic = computed<DiagnosticState>(() => {
  const cloudStatus = syncStore.status;
  if (!authStore.isAuthenticated) {
    return {
      key: "not_logged_in",
      tone: "warning",
      message: "请先登录后再使用知识库检索与 AI 问答。"
    };
  }
  if (!cloudStatus || cloudStatus.cloud_schedule_count === 0) {
    return {
      key: "no_cloud_schedules",
      tone: "warning",
      message: "当前云端还没有日程数据，请先完成同步。"
    };
  }
  if (cloudStatus.knowledge_base_eligible_schedule_count === 0) {
    return {
      key: "not_pushed",
      tone: "warning",
      message: "当前还没有允许进入知识库的云端日程，请先 Push 合适的数据。"
    };
  }
  if (cloudStatus.indexed_chunk_count === 0 || cloudStatus.last_knowledge_rebuild_status !== "success") {
    return {
      key: "pushed_not_indexed",
      tone: "warning",
      message: "知识库还没有可用索引，请先执行 Rebuild Knowledge Base。"
    };
  }
  if (lastDiagnosticKey.value === "indexed_no_hit") {
    return {
      key: "indexed_no_hit",
      tone: "info",
      message: "知识库已可用，但这次问题没有命中明显上下文，建议换个更具体的问法。"
    };
  }
  return {
    key: "ready",
    tone: "success",
    message: "当前可以直接提问，也可以在同一会话里继续追问。"
  };
});

const diagnosticToneClass = computed(() => ({
  "diagnostic-warning": diagnostic.value.tone === "warning",
  "diagnostic-info": diagnostic.value.tone === "info",
  "diagnostic-success": diagnostic.value.tone === "success"
}));

const historyTurns = computed(() => sessionTurns.value.slice(0, -1));

onMounted(async () => {
  await authStore.hydrate();
  await syncStore.initialize();
  if (authStore.isAuthenticated) {
    await syncStore.refreshStatus().catch(() => undefined);
  }
});

async function refreshStatus() {
  try {
    await syncStore.refreshStatus();
    lastDiagnosticKey.value = "ready";
    showNotify({ type: "success", message: "知识库状态已刷新。" });
  } catch (error) {
    showNotify({
      type: "danger",
      message: formatError(error, "刷新知识库状态失败。")
    });
  }
}

async function runRebuild() {
  try {
    const response = await syncStore.runRebuildKnowledgeBase();
    lastDiagnosticKey.value = "ready";
    showNotify({
      type: "success",
      message:
        response.message ??
        `已重建 ${response.schedules_indexed} / ${response.schedules_considered} 条日程，共生成 ${response.chunks_created} 个 chunks。`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "知识库重建失败。"
    });
  }
}

async function runRetrieve() {
  if (!question.value.trim()) {
    showNotify({ type: "warning", message: "请输入问题内容。" });
    return;
  }

  await syncStore.refreshStatus().catch(() => undefined);
  if (diagnostic.value.key !== "ready") {
    lastDiagnosticKey.value = diagnostic.value.key;
    showNotify({ type: "warning", message: diagnostic.value.message });
    return;
  }

  loadingRetrieve.value = true;
  answerText.value = "";
  metaInfo.value = "-";
  try {
    const result = await retrieveRagContext(question.value.trim(), 5);
    retrieved.value = result.results;
    if (result.results.length === 0) {
      lastDiagnosticKey.value = "indexed_no_hit";
      showNotify({ type: "warning", message: "当前没有检索到相关上下文。" });
      return;
    }
    lastDiagnosticKey.value = "ready";
    showNotify({ type: "success", message: `本次检索命中 ${result.results.length} 条上下文。` });
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "检索失败。") });
  } finally {
    loadingRetrieve.value = false;
  }
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `rag-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function startNewSession() {
  sessionId.value = null;
  sessionTurns.value = [];
  answerText.value = "";
  metaInfo.value = "-";
  retrieved.value = [];
}

async function runStream() {
  const trimmedQuestion = question.value.trim();
  if (!trimmedQuestion) {
    showNotify({ type: "warning", message: "请输入问题内容。" });
    return;
  }

  await syncStore.refreshStatus().catch(() => undefined);
  if (diagnostic.value.key !== "ready") {
    lastDiagnosticKey.value = diagnostic.value.key;
    showNotify({ type: "warning", message: diagnostic.value.message });
    return;
  }

  const token = await getAccessToken();
  if (!token) {
    showNotify({ type: "warning", message: "请先完成登录。" });
    return;
  }

  answerText.value = "";
  metaInfo.value = "-";
  loadingStream.value = true;
  const activeSessionId = sessionId.value ?? createSessionId();
  sessionId.value = activeSessionId;
  const activeTurn: RagConversationTurn = {
    id: `${activeSessionId}-${Date.now()}`,
    question: trimmedQuestion,
    answer: "",
    retrievedChunks: 0,
    status: "streaming"
  };
  sessionTurns.value.push(activeTurn);

  try {
    for await (const event of streamRagAnswer(trimmedQuestion, token, { topK: 5, sessionId: activeSessionId })) {
      if (event.event === "meta") {
        metaInfo.value = `本次回答使用了 ${event.data.retrieved_chunks} 条上下文。`;
        activeTurn.retrievedChunks = event.data.retrieved_chunks;
        if (event.data.retrieved_chunks === 0) {
          lastDiagnosticKey.value = "indexed_no_hit";
        }
      } else if (event.event === "token") {
        answerText.value += event.data.text;
        activeTurn.answer += event.data.text;
      } else if (event.event === "done") {
        if (event.data.message === "stream_failed") {
          activeTurn.status = "failed";
          showNotify({ type: "warning", message: "AI 流式回答中途被中断，请稍后重试。" });
          if (!answerText.value.trim()) {
            answerText.value = "AI 流式回答中途被中断，请稍后重试。";
            activeTurn.answer = answerText.value;
          }
        } else if (!answerText.value.trim()) {
          answerText.value = "AI 没有返回可显示的内容。";
          activeTurn.answer = answerText.value;
          activeTurn.status = "completed";
        } else {
          activeTurn.status = "completed";
        }
      }
    }
  } catch (error) {
    activeTurn.status = "failed";
    if (!activeTurn.answer.trim()) {
      activeTurn.answer = "AI 问答失败，请稍后重试。";
      answerText.value = activeTurn.answer;
    }
    showNotify({ type: "danger", message: formatError(error, "AI 问答失败。") });
  } finally {
    loadingStream.value = false;
  }
}

function formatTime(value: string | null): string {
  if (!value) {
    return "暂未记录";
  }
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return value;
  }
  return dt.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatError(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "response" in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: string } } }).response;
    if (maybeResponse?.data?.detail) {
      return maybeResponse.data.detail;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
</script>

<style scoped>
.rag-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.header-section {
  padding: var(--spacing-sm) var(--spacing-xs);
}

.view-title {
  margin: 0 0 var(--spacing-xs);
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-main);
}

.view-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.panel-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.status-card {
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  background: var(--bg-app);
  border: 1px solid var(--bg-subtle);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.status-value {
  color: var(--text-main);
  font-size: var(--font-size-sm);
}

.status-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-md);
}

.diagnostic-box {
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid transparent;
}

.diagnostic-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.diagnostic-message {
  line-height: 1.6;
  font-size: var(--font-size-sm);
}

.diagnostic-warning {
  background: #fffbeb;
  color: #92400e;
  border-color: #fde68a;
}

.diagnostic-info {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}

.diagnostic-success {
  background: #ecfdf5;
  color: #047857;
  border-color: #a7f3d0;
}

.custom-field {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
  background: var(--bg-app);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.session-panel {
  border: 1px solid var(--bg-subtle);
}

.session-turn-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.session-turn-card {
  background: var(--bg-surface);
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm) var(--spacing-md);
}

.session-turn-question {
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 6px;
}

.session-turn-answer {
  color: var(--text-main);
  white-space: pre-wrap;
  line-height: 1.6;
}

.session-turn-meta {
  margin-top: 8px;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.answer-panel {
  border: 1px solid var(--color-primary-soft);
  background: #fcfdfe;
}

.answer-content {
  min-height: 80px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-md);
  line-height: 1.6;
}

.loading-text {
  color: var(--text-muted);
  font-style: italic;
  margin: 0;
}

.markdown-body {
  white-space: pre-wrap;
  color: var(--text-main);
}

.meta-footer {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-sm);
  border-top: 1px dashed var(--bg-subtle);
}

.meta-text {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.chunk-card {
  background: var(--bg-surface);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  border: 1px solid var(--bg-subtle);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-xs);
}

.chunk-id {
  font-weight: 600;
  color: var(--text-secondary);
}

.chunk-score {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.chunk-content {
  font-size: var(--font-size-sm);
  color: var(--text-main);
  line-height: 1.5;
}

.rag-main-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

@media (min-width: 1024px) {
  .rag-container {
    display: grid;
    grid-template-columns: 320px 1fr;
    grid-template-rows: auto 1fr;
    gap: var(--spacing-xl);
  }

  .header-section {
    grid-column: 1 / -1;
    padding-bottom: 0;
  }

  .status-panel {
    grid-column: 1;
    grid-row: 2;
  }

  .rag-main-content {
    grid-column: 2;
    grid-row: 2;
  }
}
</style>
