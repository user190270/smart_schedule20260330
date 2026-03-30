<template>
  <div class="share-container">
    <section class="panel intro-panel">
      <h2 class="view-title">分享中心</h2>
      <p class="view-subtitle">
        只显示已经拥有云端身份的日程。生成分享后，你可以复制 UUID、复制公开链接，或直接在当前应用内打开公开预览。
      </p>
    </section>

    <section class="panel lookup-panel">
      <div class="panel-header">
        <van-icon name="search" color="var(--color-primary)" size="20" />
        <h3 class="panel-title">通过 UUID 打开分享</h3>
      </div>
      <van-field
        v-model="lookupUuid"
        label-align="top"
        label="分享 UUID"
        placeholder="输入有效的 UUID，例如 123e4567-e89b-12d3-a456-426614174000"
      />
      <div class="action-row">
        <van-button type="primary" round plain icon="arrow" :disabled="!lookupUuid.trim()" @click="openUuidLookup">
          打开公开预览
        </van-button>
      </div>
    </section>

    <section class="panel generate-panel">
      <div class="panel-header">
        <van-icon name="link-o" color="var(--color-primary)" size="20" />
        <h3 class="panel-title">为云端日程生成分享</h3>
      </div>

      <div class="share-status">
        <span>可分享的云端日程：{{ shareableSchedules.length }}</span>
        <span>仅本地日程：{{ localOnlyCount }}</span>
      </div>

      <van-empty
        v-if="shareableSchedules.length === 0"
        image="description"
        description="当前没有可分享的云端日程。请先 Push 日程到云端。"
      />

      <div v-else class="schedule-list">
        <article
          v-for="item in shareableSchedules"
          :key="item.local_id"
          class="schedule-card"
          :class="{ selected: selectedLocalId === item.local_id }"
          @click="selectedLocalId = item.local_id"
        >
          <div class="card-header">
            <h3 class="card-title">{{ item.title }}</h3>
            <div class="tag-row">
              <van-tag
                v-for="tag in localScheduleStore.describePresence(item)"
                :key="`${item.local_id}-${tag.label}`"
                :type="tag.type"
                plain
                round
              >
                {{ tag.label }}
              </van-tag>
            </div>
          </div>
          <div class="card-meta">
            <div class="meta-line">
              <van-icon name="clock-o" />
              <span>{{ formatScheduleRange(item.start_time, item.end_time) }}</span>
            </div>
            <div v-if="item.location" class="meta-line">
              <van-icon name="location-o" />
              <span>{{ item.location }}</span>
            </div>
          </div>
        </article>
      </div>

      <div class="action-row">
        <van-button
          type="primary"
          round
          icon="plus"
          :loading="loadingCreate"
          :disabled="!selectedSchedule"
          @click="createLink"
        >
          生成分享
        </van-button>
      </div>

      <van-cell-group v-if="shareUuid" inset class="custom-group result-group">
        <van-cell title="分享 UUID" :value="shareUuid" value-class="mono-text" />
        <van-cell title="公开访问链接" :value="publicShareLink" value-class="mono-text url-text" />
      </van-cell-group>

      <div v-if="shareUuid" class="action-row">
        <van-button round icon="description" type="primary" plain @click="copyUuid">复制 UUID</van-button>
        <van-button round icon="link-o" type="primary" plain @click="copyPublicLink">复制公开链接</van-button>
        <van-button round icon="eye-o" type="success" plain @click="openPreview">打开公开预览</van-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { showNotify } from "vant";

import { createShareLink } from "@/api/share";
import type { LocalScheduleRecord } from "@/repositories/local-schedules";
import { buildPublicShareLink, buildPublicSharePath } from "@/services/public-share";
import { formatScheduleRange } from "@/utils/schedule-time";
import { useAuthStore } from "@/stores/auth";
import { useCloudSyncStore } from "@/stores/cloud-sync";
import { useLocalScheduleStore } from "@/stores/local-schedules";

const router = useRouter();
const authStore = useAuthStore();
const syncStore = useCloudSyncStore();
const localScheduleStore = useLocalScheduleStore();

const loadingCreate = ref(false);
const selectedLocalId = ref<string | null>(null);
const shareUuid = ref("");
const lookupUuid = ref("");

const shareableSchedules = computed(() => localScheduleStore.shareableRecords);
const localOnlyCount = computed(
  () => localScheduleStore.visibleRecords.filter((item) => item.cloud_schedule_id === null).length
);
const selectedSchedule = computed<LocalScheduleRecord | null>(
  () => shareableSchedules.value.find((item) => item.local_id === selectedLocalId.value) ?? null
);
const publicShareLink = computed(() => (shareUuid.value ? buildPublicShareLink(shareUuid.value) : ""));

onMounted(async () => {
  await authStore.hydrate();
  await localScheduleStore.initialize();
  await syncStore.initialize();
  if (authStore.isAuthenticated) {
    await syncStore.refreshStatus().catch(() => undefined);
  }
  if (!selectedLocalId.value && shareableSchedules.value[0]) {
    selectedLocalId.value = shareableSchedules.value[0].local_id;
  }
});

async function createLink() {
  if (!selectedSchedule.value?.cloud_schedule_id) {
    showNotify({ type: "warning", message: "请先选择一条已有云端身份的日程。" });
    return;
  }

  loadingCreate.value = true;
  try {
    const result = await createShareLink(selectedSchedule.value.cloud_schedule_id);
    shareUuid.value = result.share_uuid;
    lookupUuid.value = result.share_uuid;
    showNotify({ type: "success", message: "分享已生成。你可以复制 UUID 或复制公开链接。" });
  } catch (error) {
    showNotify({ type: "danger", message: formatError(error, "生成分享失败。") });
  } finally {
    loadingCreate.value = false;
  }
}

async function copyUuid() {
  if (!shareUuid.value) {
    return;
  }
  await navigator.clipboard.writeText(shareUuid.value);
  showNotify({ type: "success", message: "已复制分享 UUID。" });
}

async function copyPublicLink() {
  if (!publicShareLink.value) {
    return;
  }
  await navigator.clipboard.writeText(publicShareLink.value);
  showNotify({ type: "success", message: "已复制公开访问链接。" });
}

async function openPreview() {
  if (!shareUuid.value) {
    return;
  }
  await router.push({ name: "share-public", params: { shareUuid: shareUuid.value } });
}

async function openUuidLookup() {
  const uuid = lookupUuid.value.trim();
  if (!uuid) {
    return;
  }
  await router.push(buildPublicSharePath(uuid));
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
.share-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
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
  line-height: 1.6;
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

.share-status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.schedule-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.schedule-card {
  border: 1px solid var(--bg-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  background: var(--bg-surface);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.schedule-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-sm);
  align-items: center;
}

.card-title {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--text-main);
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.card-meta {
  margin-top: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.meta-line {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.action-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  flex-wrap: wrap;
}

.custom-group {
  margin-top: var(--spacing-md);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--bg-subtle);
}

.mono-text {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.url-text {
  color: var(--color-primary);
  text-decoration: underline;
}
</style>
