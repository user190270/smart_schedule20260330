<template>
  <div class="home-container">
    <section class="welcome-section">
      <h1 class="welcome-title">同步与状态</h1>
      <p class="welcome-subtitle">云端连接、同步操作与知识库状态一览</p>
    </section>

    <div class="home-panels-grid">
      <section class="panel auth-panel">
        <div class="panel-header">
        <van-icon name="user-o" size="20" color="var(--color-accent)" />
        <h2 class="panel-title">账户状态</h2>
      </div>

      <div v-if="!authStore.isAuthenticated" class="auth-form-container">

        <van-form @submit="submitAuth" class="custom-form">
          <van-field v-model="username" name="username" placeholder="用户名" left-icon="contact" />
          <van-field v-model="password" name="password" type="password" placeholder="密码" left-icon="lock" />
          <div class="auth-actions">
            <van-button class="btn-primary" round block native-type="submit" :loading="loadingAuth">登录</van-button>
            <van-button class="btn-outline" round block @click="registerAccount" :loading="loadingAuth">注册并登录</van-button>
          </div>
        </van-form>
      </div>

      <div v-else class="user-profile">
        <div class="user-avatar">
          <van-icon name="smile-o" size="32" color="var(--color-primary)" />
        </div>
        <div class="user-info">
          <div class="user-name">{{ authStore.user?.username }}</div>
          <div class="user-role">{{ authStore.user?.role }}</div>
        </div>

        <div class="auth-actions-row">
          <van-button size="small" icon="replay" round @click="refreshMe" :loading="loadingAuth">刷新资料</van-button>
          <van-button size="small" icon="revoke" round plain type="danger" @click="logoutAccount" :loading="loadingAuth">
            退出登录
          </van-button>
        </div>
      </div>
    </section>

    <section class="panel sync-panel">
      <div class="panel-header">
        <van-icon name="cluster-o" size="20" color="var(--color-primary)" />
        <h2 class="panel-title">Push / Pull / Rebuild Knowledge Base</h2>
      </div>


      <div class="sync-actions">
        <van-button type="primary" round :disabled="!authStore.isAuthenticated" @click="runPush">Push</van-button>
        <van-button round :disabled="!authStore.isAuthenticated" @click="runPull">Pull</van-button>
        <van-button type="success" round plain :disabled="!authStore.isAuthenticated" @click="runRebuild">
          Rebuild Knowledge Base
        </van-button>
        <van-button size="small" icon="play-circle-o" round @click="runHealthCheck">检查连接</van-button>
      </div>

      <div class="status-grid core-stats">
        <div class="status-card">
          <span class="status-label">本地日程</span>
          <strong class="status-value status-value-lg">{{ localScheduleStore.activeCount }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">云端日程</span>
          <strong class="status-value status-value-lg">{{ syncStore.status?.cloud_schedule_count ?? 0 }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">待同步</span>
          <strong class="status-value status-value-lg" :class="{ 'text-warning': pendingSyncTotal > 0 }">{{ pendingSyncTotal }}</strong>
        </div>
        <div class="status-card">
          <span class="status-label">冲突</span>
          <strong class="status-value status-value-lg" :class="{ 'text-danger': localScheduleStore.conflictCount > 0 }">{{ localScheduleStore.conflictCount }}</strong>
        </div>
      </div>

      <div class="connection-bar">
        <span class="connection-item">
          <van-icon :name="authStore.isAuthenticated ? 'passed' : 'close'" :color="authStore.isAuthenticated ? '#137333' : '#999'" size="14" />
          {{ authStore.isAuthenticated ? '已登录' : '未登录' }}
        </span>
        <span class="connection-item">
          <van-icon :name="syncStore.healthStatus === 'connected' ? 'passed' : 'close'" :color="syncStore.healthStatus === 'connected' ? '#137333' : '#999'" size="14" />
          <span :class="connectionClass">{{ connectionLabel }}</span>
        </span>
      </div>

      <van-collapse v-model="activeCollapse" class="detail-collapse">
        <van-collapse-item title="详细状态" name="detail">
          <div class="status-grid">
            <div class="status-card">
              <span class="status-label">待上传新增</span>
              <strong class="status-value">{{ localScheduleStore.pendingCreateCount }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">待上传更新</span>
              <strong class="status-value">{{ localScheduleStore.pendingUpdateCount }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">待删除云端</span>
              <strong class="status-value">{{ localScheduleStore.pendingDeleteCloudCount }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">允许纳入知识库</span>
              <strong class="status-value">{{ syncStore.status?.knowledge_base_eligible_schedule_count ?? 0 }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">已索引日程</span>
              <strong class="status-value">{{ syncStore.status?.indexed_schedule_count ?? 0 }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">已索引 chunks</span>
              <strong class="status-value">{{ syncStore.status?.indexed_chunk_count ?? 0 }}</strong>
            </div>
            <div class="status-card">
              <span class="status-label">最近知识库重建</span>
              <strong class="status-value">{{ formatTime(syncStore.status?.last_knowledge_rebuild_at ?? null) }}</strong>
            </div>
          </div>
        </van-collapse-item>

        <van-collapse-item title="系统信息" name="system">
          <van-cell-group inset class="custom-group">
            <van-cell title="API Base URL" :value="apiBaseUrl" />
            <van-cell title="本地存储" :value="localStorageLabel" />
            <van-cell title="最近 Push 反馈" :value="syncStore.deviceMeta.lastPushMessage ?? '暂无'" />
            <van-cell title="最近 Pull 反馈" :value="syncStore.deviceMeta.lastPullMessage ?? '暂无'" />
            <van-cell title="最近知识库重建反馈" :value="syncStore.status?.last_knowledge_rebuild_message ?? '暂无'" />
          </van-cell-group>

          <div class="action-feedback">
            <div class="feedback-line">
              <span class="feedback-label">Push</span>
              <span class="feedback-text">{{ formatAction(syncStore.pushAction.status, syncStore.pushAction.message) }}</span>
            </div>
            <div class="feedback-line">
              <span class="feedback-label">Pull</span>
              <span class="feedback-text">{{ formatAction(syncStore.pullAction.status, syncStore.pullAction.message) }}</span>
            </div>
            <div class="feedback-line">
              <span class="feedback-label">重建知识库</span>
              <span class="feedback-text">
                {{ formatAction(syncStore.rebuildAction.status, syncStore.rebuildAction.message) }}
              </span>
            </div>
          </div>
        </van-collapse-item>
      </van-collapse>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { showNotify } from "vant";

import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
import { useCloudSyncStore } from "@/stores/cloud-sync";
import { useLocalScheduleStore } from "@/stores/local-schedules";

const appStore = useAppStore();
const authStore = useAuthStore();
const syncStore = useCloudSyncStore();
const localScheduleStore = useLocalScheduleStore();

const loadingAuth = ref(false);
const username = ref("demo_user");
const password = ref("demo_pass_123");
const activeCollapse = ref<string[]>([]);

const pendingSyncTotal = computed(() =>
  localScheduleStore.pendingCreateCount +
  localScheduleStore.pendingUpdateCount +
  localScheduleStore.pendingDeleteCloudCount
);

const apiBaseUrl = appStore.apiBaseUrl;

const connectionLabel = computed(() => {
  if (syncStore.healthStatus === "connected") {
    return "已连接";
  }
  if (syncStore.healthStatus === "failed") {
    return "连接失败";
  }
  return "未检查";
});

const connectionClass = computed(() => ({
  "text-success": syncStore.healthStatus === "connected",
  "text-danger": syncStore.healthStatus === "failed"
}));

const localStorageLabel = computed(() => (localScheduleStore.storageKind === "web" ? "IndexedDB" : "SQLite"));

onMounted(async () => {
  await authStore.hydrate();
  await localScheduleStore.initialize();
  await syncStore.initialize();
  if (authStore.isAuthenticated) {
    await syncStore.refreshStatus().catch(() => undefined);
  }
});

async function runHealthCheck() {
  await syncStore.checkHealth();
  showNotify({
    type: syncStore.healthStatus === "connected" ? "success" : "danger",
    message: syncStore.healthMessage ?? "连接检查已完成。"
  });
}

async function submitAuth() {
  if (!username.value || !password.value) {
    showNotify({ type: "warning", message: "请输入用户名和密码。" });
    return;
  }
  loadingAuth.value = true;
  try {
    await authStore.login({ username: username.value, password: password.value });
    await syncStore.refreshStatus().catch(() => undefined);
    showNotify({ type: "success", message: "登录成功。" });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "登录失败。"
    });
  } finally {
    loadingAuth.value = false;
  }
}

async function registerAccount() {
  if (!username.value || !password.value) {
    showNotify({ type: "warning", message: "请输入用户名和密码。" });
    return;
  }
  loadingAuth.value = true;
  try {
    await authStore.register({ username: username.value, password: password.value });
    await syncStore.refreshStatus().catch(() => undefined);
    showNotify({ type: "success", message: "注册并登录成功。" });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "注册失败。"
    });
  } finally {
    loadingAuth.value = false;
  }
}

async function refreshMe() {
  loadingAuth.value = true;
  try {
    await authStore.refreshProfile();
    await syncStore.refreshStatus().catch(() => undefined);
    showNotify({ type: "success", message: "账户信息已刷新。" });
  } finally {
    loadingAuth.value = false;
  }
}

async function logoutAccount() {
  loadingAuth.value = true;
  try {
    await authStore.logout();
    syncStore.clearCloudStatus();
    showNotify({ type: "success", message: "已退出登录，本地日程仍可继续使用。" });
  } finally {
    loadingAuth.value = false;
  }
}

async function runPush() {
  if (!authStore.isAuthenticated) {
    showNotify({ type: "warning", message: "请先登录后再执行 Push。" });
    return;
  }
  try {
    const response = await syncStore.runPush();
    const created = response.results.filter((item) => item.status === "created").length;
    const updated = response.results.filter((item) => item.status === "updated").length;
    const ignored = response.results.filter((item) => item.status === "ignored").length;
    showNotify({
      type: "success",
      message: `Push 完成：新增 ${created} 条，更新 ${updated} 条，忽略 ${ignored} 条。`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "Push 失败。"
    });
  }
}

async function runPull() {
  if (!authStore.isAuthenticated) {
    showNotify({ type: "warning", message: "请先登录后再执行 Pull。" });
    return;
  }
  try {
    const response = await syncStore.runPull();
    const activeCloudCount = response.records.filter((record) => !record.is_deleted).length;
    showNotify({
      type: "success",
      message: `Pull 完成：合并了 ${activeCloudCount} 条云端日程。`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "Pull 失败。"
    });
  }
}

async function runRebuild() {
  if (!authStore.isAuthenticated) {
    showNotify({ type: "warning", message: "请先登录后再重建知识库。" });
    return;
  }
  try {
    const response = await syncStore.runRebuildKnowledgeBase();
    showNotify({
      type: "success",
      message:
        response.message ??
        `已重建 ${response.schedules_indexed} / ${response.schedules_considered} 条日程，生成 ${response.chunks_created} 个 chunks。`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "知识库重建失败。"
    });
  }
}

function formatTime(value: string | null): string {
  if (!value) {
    return "暂无";
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

function formatAction(status: string, message: string | null): string {
  if ((status === "success" || status === "failure") && message) {
    return message;
  }
  return "暂无";
}
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.welcome-section {
  text-align: center;
  padding: var(--spacing-md) 0;
}

.welcome-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 var(--spacing-xs);
}

.welcome-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.7;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.panel-header .panel-title {
  margin: 0;
}

.panel-subtitle {
  margin: 0 0 var(--spacing-md);
  color: var(--text-secondary);
  line-height: 1.6;
}

.auth-actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

.btn-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.btn-outline {
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  background: transparent;
}

.user-profile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
}

.user-avatar {
  background: var(--color-primary-soft);
  width: 64px;
  height: 64px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-info {
  text-align: center;
}

.user-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-main);
}

.user-role {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-transform: capitalize;
}

.auth-actions-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.sync-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-md);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.core-stats .status-card {
  text-align: center;
  padding: var(--spacing-md) var(--spacing-sm);
}

.status-value-lg {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.connection-bar {
  display: flex;
  gap: var(--spacing-lg);
  justify-content: center;
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-collapse {
  margin-bottom: var(--spacing-md);
}

.detail-collapse .status-grid {
  margin-bottom: 0;
}

.text-warning {
  color: #e37400;
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

.custom-group {
  margin: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--bg-subtle);
}

.action-feedback {
  margin-top: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.feedback-line {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-start;
}

.feedback-label {
  min-width: 88px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.feedback-text {
  color: var(--text-main);
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.text-success {
  color: #137333;
}

.text-danger {
  color: #c5221f;
}

.home-panels-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

@media (min-width: 1024px) {
  .home-panels-grid {
    display: grid;
    grid-template-columns: 340px 1fr;
    align-items: start;
    gap: var(--spacing-xl);
  }

  .welcome-section {
    text-align: left;
    padding: var(--spacing-sm) 0;
  }
}
</style>
