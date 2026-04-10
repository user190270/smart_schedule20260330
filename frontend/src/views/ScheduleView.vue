<template>
  <div class="schedule-container">
    <div class="header-actions">
      <div class="title-group">
        <h2 class="view-title">日程</h2>
        <span class="view-subtitle">
          本地日程 {{ localScheduleStore.activeCount }} 条
          <template v-if="authStore.isAuthenticated">
            · 云端日程 {{ syncStore.status?.cloud_schedule_count ?? 0 }} 条
          </template>
        </span>
      </div>
      <div class="action-buttons">
        <van-button icon="plus" type="primary" size="small" round @click="openCreate">新建日程</van-button>
      </div>
    </div>



    <section class="panel filter-panel">
      <van-tabs v-model:active="activeFilter" shrink animated>
        <van-tab title="全部" name="all" />
        <van-tab title="本地" name="local" />
        <van-tab title="云端" name="cloud" />
      </van-tabs>
      <p v-if="authStore.isAuthenticated && localScheduleStore.hiddenOtherAccountCount > 0" class="ownership-note">
        已隐藏 {{ localScheduleStore.hiddenOtherAccountCount }} 条其他账号的本地记录
      </p>
    </section>

    <section v-if="authStore.isAuthenticated" class="panel email-config-panel">
      <div class="panel-header">
        <van-icon name="envelop-o" />
        <h3 class="panel-title">邮件提醒配置</h3>
      </div>
      <p class="panel-caption">默认关闭，仅对已同步到云端的日程开放邮件提醒。</p>
      <van-field
        v-model="notificationEmail"
        label-align="top"
        label="接收邮箱"
        type="email"
        placeholder="name@example.com"
      />
      <p class="email-help">
        {{
          authStore.user?.notification_email
            ? `当前已保存：${authStore.user.notification_email}`
            : "尚未保存接收邮箱。"
        }}
      </p>
      <div class="profile-actions">
        <van-button round size="small" type="primary" :loading="savingProfile" @click="saveNotificationEmail">
          保存邮箱
        </van-button>
        <van-button
          round
          size="small"
          plain
          :loading="savingProfile"
          :disabled="!notificationEmail && !authStore.user?.notification_email"
          @click="clearNotificationEmail"
        >
          清空
        </van-button>
      </div>
    </section>

    <van-empty
      v-if="visibleSchedules.length === 0"
      image="search"
      description="当前筛选条件下还没有日程。"
      class="empty-state"
    >
      <van-button round type="primary" class="bottom-button" @click="openCreate">创建第一条日程</van-button>
    </van-empty>

    <div v-else class="schedule-list">
      <article v-for="item in visibleSchedules" :key="item.local_id" class="schedule-card">
        <div class="card-header">
          <div class="card-title-group">
            <h3 class="card-title">{{ item.title }}</h3>
            <div class="tag-row">
              <van-tag
                v-for="tag in localScheduleStore.describeTags(item)"
                :key="`${item.local_id}-${tag.label}`"
                :type="tag.type"
                plain
                round
              >
                {{ tag.label }}
              </van-tag>
            </div>
          </div>
          <div class="card-actions">
            <van-button
              v-if="item.sync_intent === 'conflict'"
              size="mini"
              plain
              round
              type="danger"
              @click="openConflictSheet(item)"
            >
              解决冲突
            </van-button>
            <van-icon name="edit" class="action-icon" @click="openEdit(item)" />
            <van-icon name="delete-o" class="action-icon text-danger" @click="openDeleteMenu(item)" />
          </div>
        </div>

        <div class="card-body">
          <div class="meta-line">
            <van-icon name="clock-o" />
            <span>{{ formatScheduleRange(item.start_time, item.end_time) }}</span>
          </div>
          <div v-if="item.location" class="meta-line">
            <van-icon name="location-o" />
            <span>{{ item.location }}</span>
          </div>
          <div v-if="item.remark" class="remark-block">
            {{ item.remark }}
          </div>
          <div class="status-line">
            <span>同步状态：{{ localScheduleStore.syncStateLabel(item.sync_intent) }}</span>
            <span>存储策略：{{ localScheduleStore.storageStrategyLabel(item.storage_strategy) }}</span>
          </div>
        </div>
      </article>
    </div>

    <van-popup v-model:show="showEditor" position="bottom" round class="editor-popup" closeable>
      <div class="editor-content">
        <div class="editor-header">
          <h3 class="editor-title">{{ editingLocalId ? "编辑日程" : "新建日程" }}</h3>

        </div>

        <van-form @submit="submitForm" class="custom-form">
          <van-field
            v-model="form.title"
            label-align="top"
            label="标题"
            name="title"
            required
            placeholder="例如：和 Alice 的项目同步"
          />
          <div class="datetime-row">
            <van-field
              v-model="form.start_time"
              label-align="top"
              label="开始时间"
              name="start"
              placeholder="YYYY-MM-DDTHH:mm:ss"
            />
            <van-field
              v-model="form.end_time"
              label-align="top"
              label="结束时间"
              name="end"
              placeholder="YYYY-MM-DDTHH:mm:ss"
            />
          </div>
          <van-field v-model="form.location" label-align="top" label="地点" name="location" placeholder="例如：图书馆 2 楼" />
          <van-field
            v-model="form.remark"
            label-align="top"
            label="备注"
            name="remark"
            type="textarea"
            rows="3"
            autosize
            placeholder="补充说明、准备事项或关键词"
          />

          <div class="strategy-section">
            <div class="strategy-title">存储策略</div>
            <div class="strategy-options">
              <button
                v-for="option in strategyOptions"
                :key="option.value"
                type="button"
                class="strategy-option"
                :class="{ active: form.storage_strategy === option.value }"
                @click="form.storage_strategy = option.value"
              >
                <strong>{{ option.label }}</strong>
                <span>{{ option.hint }}</span>
              </button>
            </div>
          </div>

          <div v-if="authStore.isAuthenticated" class="strategy-section reminder-section">
            <div class="strategy-title">云端邮件提醒</div>
            <p class="reminder-help">{{ reminderHelpText }}</p>
            <div class="strategy-options reminder-toggle-row">
              <button
                type="button"
                class="strategy-option"
                :class="{ active: form.email_reminder_enabled }"
                :disabled="!canConfigureEmailReminder"
                @click="setEmailReminderEnabled(true)"
              >
                <strong>启用邮件提醒</strong>
                <span>{{ selectedReminderLeadLabel }}</span>
              </button>
              <button
                type="button"
                class="strategy-option"
                :class="{ active: !form.email_reminder_enabled }"
                @click="setEmailReminderEnabled(false)"
              >
                <strong>关闭邮件提醒</strong>
                <span>默认关闭，不影响移动端本地通知。</span>
              </button>
            </div>
            <div v-if="form.email_reminder_enabled" class="reminder-presets">
              <button
                v-for="option in reminderLeadOptions"
                :key="option.value"
                type="button"
                class="reminder-chip"
                :class="{ active: form.email_remind_before_minutes === option.value }"
                @click="selectReminderLead(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="editor-actions">
            <van-button round block type="primary" native-type="submit" :loading="saving">保存日程</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <van-popup v-model:show="showDeleteSheet" position="bottom" round class="delete-popup" closeable>
      <div class="delete-sheet">
        <div class="panel-header">
          <van-icon name="warning-o" color="#dc2626" />
          <h3 class="panel-title">删除...</h3>
        </div>
        <p class="delete-subtitle">{{ deleteTarget?.title }}</p>
        <button
          v-for="option in deleteOptions"
          :key="option.key"
          type="button"
          class="delete-option"
          @click="confirmDeleteOption(option.key)"
        >
          <strong>{{ option.label }}</strong>
          <span>{{ option.description }}</span>
        </button>
      </div>
    </van-popup>

    <van-popup v-model:show="showConflictSheet" position="bottom" round class="conflict-popup" closeable>
      <div v-if="conflictDetails" class="conflict-sheet">
        <div class="panel-header">
          <van-icon name="warning-o" color="#dc2626" />
          <h3 class="panel-title">解决冲突</h3>
        </div>
        <p class="delete-subtitle">{{ conflictDetails.title }}</p>
        <p class="conflict-reason">{{ conflictDetails.reason }}</p>
        <div class="conflict-meta">
          <span>本地更新时间：{{ formatScheduleDateTime(conflictDetails.local_updated_at) }}</span>
          <span>云端更新时间：{{ formatScheduleDateTime(conflictDetails.cloud_updated_at) }}</span>
        </div>

        <div class="conflict-compare">
          <section class="conflict-version-card">
            <h4>本地版本</h4>
            <div class="conflict-field">
              <strong>标题</strong>
              <span>{{ conflictDetails.local_version.title }}</span>
            </div>
            <div class="conflict-field">
              <strong>时间</strong>
              <span>{{ formatScheduleRange(conflictDetails.local_version.start_time, conflictDetails.local_version.end_time) }}</span>
            </div>
            <div class="conflict-field">
              <strong>地点</strong>
              <span>{{ conflictDetails.local_version.location || "未设置" }}</span>
            </div>
            <div class="conflict-field">
              <strong>备注</strong>
              <span>{{ conflictDetails.local_version.remark || "未设置" }}</span>
            </div>
          </section>

          <section class="conflict-version-card">
            <h4>云端版本</h4>
            <template v-if="conflictDetails.cloud_version">
              <div class="conflict-field">
                <strong>标题</strong>
                <span>{{ conflictDetails.cloud_version.title }}</span>
              </div>
              <div class="conflict-field">
                <strong>时间</strong>
                <span>{{ formatScheduleRange(conflictDetails.cloud_version.start_time, conflictDetails.cloud_version.end_time) }}</span>
              </div>
              <div class="conflict-field">
                <strong>地点</strong>
                <span>{{ conflictDetails.cloud_version.location || "未设置" }}</span>
              </div>
              <div class="conflict-field">
                <strong>备注</strong>
                <span>{{ conflictDetails.cloud_version.remark || "未设置" }}</span>
              </div>
            </template>
            <p v-else class="conflict-empty">
              当前还没有完整的云端版本快照。请先执行 Pull 刷新冲突信息。
            </p>
          </section>
        </div>

        <div class="conflict-actions">
          <van-button round block type="danger" plain @click="resolveConflict('accept_cloud')">
            采用云端版本
          </van-button>
          <van-button round block type="primary" @click="resolveConflict('keep_local')">
            保留本地版本并在下次 Push 覆盖云端
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { showConfirmDialog, showNotify } from "vant";

import type { LocalScheduleRecord } from "@/repositories/local-schedules";
import { useAuthStore } from "@/stores/auth";
import { useCloudSyncStore } from "@/stores/cloud-sync";
import { useLocalScheduleStore, type ConflictDetails, type ConflictResolutionAction } from "@/stores/local-schedules";
import { formatScheduleDateTime, formatScheduleRange } from "@/utils/schedule-time";

type FilterMode = "all" | "local" | "cloud";

const authStore = useAuthStore();
const syncStore = useCloudSyncStore();
const localScheduleStore = useLocalScheduleStore();

const saving = ref(false);
const showEditor = ref(false);
const showDeleteSheet = ref(false);
const showConflictSheet = ref(false);
const activeFilter = ref<FilterMode>("all");
const editingLocalId = ref<string | null>(null);
const deleteTarget = ref<LocalScheduleRecord | null>(null);
const conflictLocalId = ref<string | null>(null);
const notificationEmail = ref("");
const savingProfile = ref(false);

const form = ref({
  title: "",
  start_time: "",
  end_time: "",
  location: "",
  remark: "",
  storage_strategy: "local_only" as LocalScheduleRecord["storage_strategy"],
  email_reminder_enabled: false,
  email_remind_before_minutes: 10 as number | null
});

const storageLabel = computed(() => (localScheduleStore.storageKind === "web" ? "IndexedDB" : "SQLite"));
const strategyOptions = computed(() => localScheduleStore.storageStrategyOptions());
const reminderLeadOptions = [
  { label: "到点提醒", value: 0 },
  { label: "提前 1 分钟", value: 1 },
  { label: "提前 5 分钟", value: 5 },
  { label: "提前 10 分钟", value: 10 },
  { label: "提前 30 分钟", value: 30 }
] as const;

const visibleSchedules = computed(() =>
  localScheduleStore.visibleRecords.filter((record) => localScheduleStore.presenceFilterMatches(record, activeFilter.value))
);
const editingRecord = computed(() =>
  editingLocalId.value ? localScheduleStore.getRecordByLocalId(editingLocalId.value) : null
);
const hasNotificationEmail = computed(() => Boolean(authStore.user?.notification_email?.trim()));
const canConfigureEmailReminder = computed(
  () =>
    Boolean(
      authStore.isAuthenticated &&
        hasNotificationEmail.value &&
        editingRecord.value?.cloud_schedule_id !== null &&
        form.value.storage_strategy !== "local_only"
    )
);
const reminderHelpText = computed(() => {
  if (!authStore.isAuthenticated) {
    return "登录后才可以配置云端邮件提醒。";
  }
  if (!hasNotificationEmail.value) {
    return "请先保存接收邮箱，然后才能为云端日程开启邮件提醒。";
  }
  if (!editingLocalId.value || editingRecord.value?.cloud_schedule_id === null) {
    return "仅已同步到云端的日程支持邮件提醒。请先保存并完成一次云端同步。";
  }
  if (form.value.storage_strategy === "local_only") {
    return "当前保存策略为仅本地。邮件提醒仅支持已同步到云端的日程。";
  }
  return "邮件提醒会按预设提前量发送，不会替代移动端本地通知。";
});
const selectedReminderLeadLabel = computed(() => {
  const selected = reminderLeadOptions.find((option) => option.value === form.value.email_remind_before_minutes);
  return selected?.label ?? "提前 10 分钟";
});

const deleteOptions = computed(() => {
  if (!deleteTarget.value) {
    return [];
  }
  return localScheduleStore.getDeleteOptions(deleteTarget.value);
});

const conflictDetails = computed<ConflictDetails | null>(() => {
  if (!conflictLocalId.value) {
    return null;
  }
  return localScheduleStore.getConflictDetails(conflictLocalId.value);
});

onMounted(async () => {
  await authStore.hydrate();
  await localScheduleStore.initialize();
  await syncStore.initialize();
  if (authStore.isAuthenticated) {
    await syncStore.refreshStatus().catch(() => undefined);
  }
});

watch(
  () => authStore.user?.notification_email,
  (value) => {
    notificationEmail.value = value ?? "";
  },
  { immediate: true }
);

watch(
  canConfigureEmailReminder,
  (enabled) => {
    if (!enabled) {
      form.value.email_reminder_enabled = false;
      form.value.email_remind_before_minutes = 10;
    }
  },
  { immediate: true }
);

function openCreate() {
  editingLocalId.value = null;
  form.value = {
    title: "",
    start_time: new Date().toISOString(),
    end_time: "",
    location: "",
    remark: "",
    storage_strategy: authStore.isAuthenticated ? "sync_to_cloud" : "local_only",
    email_reminder_enabled: false,
    email_remind_before_minutes: 10
  };
  showEditor.value = true;
}

function openEdit(item: LocalScheduleRecord) {
  editingLocalId.value = item.local_id;
  form.value = {
    title: item.title,
    start_time: item.start_time,
    end_time: item.end_time ?? "",
    location: item.location ?? "",
    remark: item.remark ?? "",
    storage_strategy: item.storage_strategy,
    email_reminder_enabled: item.email_reminder_enabled,
    email_remind_before_minutes: item.email_remind_before_minutes ?? 10
  };
  showEditor.value = true;
}

function setEmailReminderEnabled(enabled: boolean) {
  if (!enabled) {
    form.value.email_reminder_enabled = false;
    form.value.email_remind_before_minutes = 10;
    return;
  }

  if (!canConfigureEmailReminder.value) {
    showNotify({ type: "warning", message: reminderHelpText.value });
    return;
  }

  form.value.email_reminder_enabled = true;
  if (form.value.email_remind_before_minutes == null) {
    form.value.email_remind_before_minutes = 10;
  }
}

function selectReminderLead(minutes: number) {
  if (!canConfigureEmailReminder.value) {
    showNotify({ type: "warning", message: reminderHelpText.value });
    return;
  }
  form.value.email_reminder_enabled = true;
  form.value.email_remind_before_minutes = minutes;
}

async function saveNotificationEmail() {
  if (!authStore.isAuthenticated) {
    return;
  }

  savingProfile.value = true;
  try {
    const trimmed = notificationEmail.value.trim();
    await authStore.updateProfile({
      notification_email: trimmed || null
    });
    notificationEmail.value = authStore.user?.notification_email ?? "";
    showNotify({ type: "success", message: "提醒邮箱已保存。" });
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "保存提醒邮箱失败。") });
  } finally {
    savingProfile.value = false;
  }
}

async function clearNotificationEmail() {
  notificationEmail.value = "";
  await saveNotificationEmail();
}

async function submitForm() {
  if (!form.value.title.trim() || !form.value.start_time) {
    showNotify({ type: "warning", message: "请填写标题和开始时间。" });
    return;
  }

  saving.value = true;
  try {
    if (editingLocalId.value) {
      await localScheduleStore.updateSchedule(editingLocalId.value, {
        title: form.value.title.trim(),
        start_time: form.value.start_time,
        end_time: form.value.end_time || null,
        location: form.value.location || null,
        remark: form.value.remark || null,
        storage_strategy: form.value.storage_strategy,
        email_reminder_enabled: form.value.email_reminder_enabled,
        email_remind_before_minutes: form.value.email_remind_before_minutes
      });
      showNotify({ type: "success", message: "日程已更新。" });
    } else {
      await localScheduleStore.createSchedule({
        title: form.value.title.trim(),
        start_time: form.value.start_time,
        end_time: form.value.end_time || null,
        location: form.value.location || null,
        remark: form.value.remark || null,
        storage_strategy: form.value.storage_strategy,
        email_reminder_enabled: form.value.email_reminder_enabled,
        email_remind_before_minutes: form.value.email_remind_before_minutes
      });
      showNotify({ type: "success", message: "日程已保存到本地仓。" });
    }

    showEditor.value = false;
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "保存日程失败。") });
  } finally {
    saving.value = false;
  }
}

function openDeleteMenu(item: LocalScheduleRecord) {
  deleteTarget.value = item;
  showDeleteSheet.value = true;
}

function openConflictSheet(item: LocalScheduleRecord) {
  conflictLocalId.value = item.local_id;
  showConflictSheet.value = true;
}

async function confirmDeleteOption(actionKey: "delete_local" | "delete_cloud_keep_local" | "delete_both") {
  const target = deleteTarget.value;
  const option = deleteOptions.value.find((item) => item.key === actionKey);
  if (!target || !option) {
    return;
  }

  try {
    await showConfirmDialog({
      title: option.confirmTitle,
      message: option.confirmMessage,
      confirmButtonText: "确认",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }

  try {
    await localScheduleStore.applyDeleteAction(target.local_id, actionKey);
    showDeleteSheet.value = false;

    if (actionKey === "delete_local") {
      showNotify({ type: "success", message: "删除操作已完成。" });
    } else if (actionKey === "delete_cloud_keep_local") {
      showNotify({ type: "success", message: "已标记为待删除云端，等待下一次 Push 执行。" });
    } else {
      showNotify({ type: "success", message: "已标记为同时删除本地与云端，等待下一次 Push 完成。" });
    }
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "删除日程失败。") });
  }
}

async function resolveConflict(action: ConflictResolutionAction) {
  if (!conflictLocalId.value) {
    return;
  }

  const message =
    action === "accept_cloud"
      ? "确认采用云端版本覆盖本地吗？当前本地修改会被云端版本替换。"
      : "确认保留本地版本吗？系统会把它重新标记为待上传更新，并在下一次 Push 时覆盖云端。";

  try {
    await showConfirmDialog({
      title: action === "accept_cloud" ? "采用云端版本" : "保留本地版本",
      message,
      confirmButtonText: "确认",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }

  try {
    await localScheduleStore.resolveConflict(conflictLocalId.value, action);
    showConflictSheet.value = false;
    conflictLocalId.value = null;
    const notifyMessage =
      action === "accept_cloud"
        ? "已采用云端版本，本地记录已恢复为已同步状态。"
        : "已保留本地版本，并重新标记为待上传更新。下一次 Push 会覆盖云端。";
    showNotify({ type: "success", message: notifyMessage });
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "解决同步冲突失败。") });
  }
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
.schedule-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--spacing-xs);
  gap: var(--spacing-md);
}

.title-group {
  display: flex;
  flex-direction: column;
}

.view-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-main);
}

.view-subtitle {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: var(--spacing-sm);
}

.guidance-text,
.filter-hint {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.summary-pill {
  font-size: var(--font-size-xs);
  color: var(--text-main);
  background: var(--bg-app);
  border: 1px solid var(--bg-subtle);
  border-radius: 999px;
  padding: 4px 10px;
}

.ownership-note {
  margin: var(--spacing-sm) 0 0;
  color: #92400e;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  line-height: 1.6;
}

.email-config-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.panel-caption,
.email-help,
.reminder-help {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.profile-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.empty-state {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: var(--spacing-xl) 0;
}

.bottom-button {
  width: 180px;
  height: 40px;
}

.schedule-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

@media (min-width: 1024px) {
  .schedule-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: var(--spacing-lg);
  }
}

.schedule-card {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-md);
  border: 1px solid var(--bg-subtle);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.card-title-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.card-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.3;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--text-muted);
}

.action-icon {
  font-size: 20px;
  padding: 4px;
}

.text-danger {
  color: #dc2626;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.meta-line {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.remark-block {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--bg-app);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-primary-soft);
  white-space: pre-wrap;
  line-height: 1.5;
  color: var(--text-secondary);
}

.status-line {
  margin-top: var(--spacing-sm);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.panel-title {
  margin: 0;
}

.editor-popup,
.delete-popup,
.conflict-popup {
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.editor-content,
.delete-sheet,
.conflict-sheet {
  padding: var(--spacing-xl) var(--spacing-md) var(--spacing-lg);
  flex: 1;
  overflow-y: auto;
}

.editor-header {
  margin-bottom: var(--spacing-lg);
}

.editor-title {
  margin: 0 0 var(--spacing-xs);
  font-size: var(--font-size-xl);
  font-weight: 600;
}

.editor-subtitle,
.delete-subtitle {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.datetime-row {
  display: flex;
  gap: var(--spacing-sm);
}

.strategy-section {
  margin-top: var(--spacing-lg);
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

.strategy-option,
.delete-option {
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

.strategy-option strong,
.delete-option strong {
  color: var(--text-main);
  font-size: var(--font-size-sm);
}

.strategy-option span,
.delete-option span {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.6;
}

.reminder-presets {
  margin-top: var(--spacing-sm);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.reminder-chip {
  border: 1px solid var(--bg-subtle);
  border-radius: 999px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  padding: 8px 14px;
  font-size: var(--font-size-xs);
}

.reminder-chip.active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.08);
}

.delete-option + .delete-option {
  margin-top: var(--spacing-sm);
}

.conflict-reason {
  margin: var(--spacing-sm) 0 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.conflict-meta {
  margin-top: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.conflict-compare {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
}

.conflict-version-card {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.conflict-version-card h4 {
  margin: 0;
  color: var(--text-main);
}

.conflict-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conflict-field strong {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.conflict-field span,
.conflict-empty {
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.conflict-actions {
  margin-top: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.editor-actions {
  margin-top: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
}

@media (max-width: 640px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .datetime-row {
    flex-direction: column;
  }

  .conflict-compare {
    grid-template-columns: 1fr;
  }
}
</style>
