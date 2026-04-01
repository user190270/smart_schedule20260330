<template>
  <div class="admin-page">
    <van-nav-bar title="管理员后台" left-text="返回首页" left-arrow @click-left="goHome" />

    <section class="panel admin-intro">
      <h2 class="panel-title">用户与配额管理</h2>
      <p class="panel-subtitle">
        这里是管理员专用的 Web 管理页面，用于查看用户状态、启用或禁用账号，以及重置每日 token 配额。
      </p>
      <div class="admin-toolbar">
        <van-button type="primary" round size="small" @click="loadUsers" :loading="loadingUsers">刷新用户列表</van-button>
      </div>
    </section>

    <section class="stats-grid">
      <div class="panel stat-card">
        <span class="stat-label">用户总数</span>
        <strong class="stat-value">{{ users.length }}</strong>
      </div>
      <div class="panel stat-card">
        <span class="stat-label">管理员</span>
        <strong class="stat-value">{{ adminCount }}</strong>
      </div>
      <div class="panel stat-card">
        <span class="stat-label">启用中</span>
        <strong class="stat-value">{{ activeCount }}</strong>
      </div>
      <div class="panel stat-card">
        <span class="stat-label">已禁用</span>
        <strong class="stat-value">{{ disabledCount }}</strong>
      </div>
    </section>

    <section v-if="errorMessage" class="panel error-panel">
      <h3 class="panel-title">加载失败</h3>
      <p class="panel-subtitle">{{ errorMessage }}</p>
    </section>

    <section v-if="loadingUsers" class="panel loading-panel">
      <van-loading size="24px" vertical>正在加载管理员数据...</van-loading>
    </section>

    <section v-else-if="!users.length" class="panel empty-panel">
      <van-empty description="当前没有可管理的用户数据" />
    </section>

    <section v-else class="user-list">
      <article v-for="user in users" :key="user.id" class="panel user-card">
        <div class="user-card-head">
          <div>
            <div class="user-name">{{ user.username }}</div>
            <div class="user-meta">
              <span class="meta-text">用户 ID：{{ user.id }}</span>
              <span class="meta-text">角色：{{ formatRole(user.role) }}</span>
            </div>
          </div>
          <div class="tag-group">
            <span class="badge" :class="user.is_active ? 'badge-active' : 'badge-inactive'">
              {{ user.is_active ? "已启用" : "已禁用" }}
            </span>
            <span class="badge" :class="user.role === 'admin' ? 'badge-admin' : 'badge-user'">
              {{ formatRole(user.role) }}
            </span>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">今日配额使用</span>
            <strong class="detail-value">{{ user.daily_token_usage }}</strong>
          </div>
          <div class="detail-item">
            <span class="detail-label">最近重置时间</span>
            <strong class="detail-value">{{ formatTime(user.last_reset_time) }}</strong>
          </div>
        </div>

        <p v-if="isCurrentAdmin(user)" class="self-note">
          当前登录管理员可查看自身状态，但此页不提供禁用自身账号的快捷操作。
        </p>

        <div class="action-row">
          <van-button
            round
            plain
            size="small"
            :type="user.is_active ? 'danger' : 'primary'"
            :disabled="isCurrentAdmin(user)"
            :loading="pendingAction === 'toggle' && pendingUserId === user.id"
            @click="confirmToggle(user)"
          >
            {{ user.is_active ? "禁用账号" : "启用账号" }}
          </van-button>
          <van-button
            round
            plain
            size="small"
            type="primary"
            :loading="pendingAction === 'quota' && pendingUserId === user.id"
            @click="confirmResetQuota(user)"
          >
            重置今日配额
          </van-button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { showConfirmDialog, showNotify } from "vant";
import { useRouter } from "vue-router";

import { listAdminUsers, updateAdminUser, type AdminUserView } from "@/api/admin";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const users = ref<AdminUserView[]>([]);
const loadingUsers = ref(false);
const errorMessage = ref("");
const pendingUserId = ref<number | null>(null);
const pendingAction = ref<"toggle" | "quota" | null>(null);

const adminCount = computed(() => users.value.filter((user) => user.role === "admin").length);
const activeCount = computed(() => users.value.filter((user) => user.is_active).length);
const disabledCount = computed(() => users.value.filter((user) => !user.is_active).length);

onMounted(async () => {
  await authStore.hydrate();
  await loadUsers();
});

async function loadUsers() {
  loadingUsers.value = true;
  errorMessage.value = "";
  try {
    users.value = await listAdminUsers();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "管理员数据加载失败。";
  } finally {
    loadingUsers.value = false;
  }
}

function goHome() {
  void router.push("/");
}

function formatRole(role: AdminUserView["role"]): string {
  return role === "admin" ? "管理员" : "普通用户";
}

function formatTime(value: string): string {
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return value;
  }
  return dt.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function isCurrentAdmin(user: AdminUserView): boolean {
  return authStore.user?.id === user.id;
}

function replaceUser(updated: AdminUserView) {
  const index = users.value.findIndex((item) => item.id === updated.id);
  if (index >= 0) {
    users.value.splice(index, 1, updated);
  }
}

async function confirmToggle(user: AdminUserView) {
  const targetState = !user.is_active;
  try {
    await showConfirmDialog({
      title: user.is_active ? "确认禁用用户" : "确认启用用户",
      message: user.is_active
        ? `确认禁用用户 ${user.username} 吗？禁用后该用户将无法继续使用受保护接口。`
        : `确认重新启用用户 ${user.username} 吗？`
    });
  } catch {
    return;
  }

  pendingUserId.value = user.id;
  pendingAction.value = "toggle";
  try {
    const updated = await updateAdminUser(user.id, { is_active: targetState });
    replaceUser(updated);
    showNotify({
      type: "success",
      message: targetState ? `已启用 ${user.username}` : `已禁用 ${user.username}`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "更新用户状态失败。"
    });
  } finally {
    pendingUserId.value = null;
    pendingAction.value = null;
  }
}

async function confirmResetQuota(user: AdminUserView) {
  try {
    await showConfirmDialog({
      title: "确认重置配额",
      message: `确认将 ${user.username} 的今日 token 使用量重置为 0 吗？`
    });
  } catch {
    return;
  }

  pendingUserId.value = user.id;
  pendingAction.value = "quota";
  try {
    const updated = await updateAdminUser(user.id, { reset_quota: true });
    replaceUser(updated);
    showNotify({
      type: "success",
      message: `已重置 ${user.username} 的今日配额`
    });
  } catch (error) {
    showNotify({
      type: "danger",
      message: error instanceof Error ? error.message : "重置配额失败。"
    });
  } finally {
    pendingUserId.value = null;
    pendingAction.value = null;
  }
}
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--bg-app);
  padding-bottom: var(--spacing-xl);
}

.admin-page :deep(.van-nav-bar) {
  position: sticky;
  top: 0;
  z-index: 20;
}

.admin-intro,
.stats-grid,
.user-list,
.error-panel,
.loading-panel,
.empty-panel {
  margin: var(--spacing-md);
}

.admin-toolbar {
  display: flex;
  justify-content: flex-end;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.stat-value {
  font-size: var(--font-size-xl);
  color: var(--text-main);
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.user-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.user-card-head {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.user-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-main);
}

.user-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xs);
}

.meta-text {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--spacing-xs);
}

.badge-active {
  background: #eaf7ee;
  color: #137333;
}

.badge-inactive {
  background: #fce8e6;
  color: #c5221f;
}

.badge-admin {
  background: #fff3e5;
  color: #b65a00;
}

.badge-user {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.detail-item {
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  background: var(--bg-app);
  border: 1px solid var(--bg-subtle);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
}

.detail-value {
  color: var(--text-main);
  font-size: var(--font-size-sm);
}

.self-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

@media (min-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-lg);
  }

  .user-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: var(--spacing-lg);
  }
}
</style>
