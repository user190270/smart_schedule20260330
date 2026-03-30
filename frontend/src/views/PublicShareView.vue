<template>
  <div class="public-share">
    <section class="panel" v-if="loading">
      <div class="panel-header">
        <van-icon name="clock-o" color="var(--color-primary)" />
        <h2 class="panel-title">正在加载公开分享</h2>
      </div>
      <p class="panel-subtitle">请稍候，系统正在根据 UUID 读取分享内容。</p>
    </section>

    <section v-else-if="errorMessage" class="panel error-panel">
      <div class="panel-header">
        <van-icon name="warning-o" color="#dc2626" />
        <h2 class="panel-title">无法打开公开分享</h2>
      </div>
      <p class="panel-subtitle">{{ errorMessage }}</p>
    </section>

    <section v-else-if="shared" class="panel preview-panel">
      <div class="panel-header">
        <van-icon name="link-o" color="var(--color-primary)" />
        <h2 class="panel-title">公开分享预览</h2>
      </div>
      <div class="share-meta">分享 UUID：{{ shareUuid }}</div>
      <h1 class="share-title">{{ shared.title }}</h1>
      <div class="meta-line">
        <van-icon name="clock-o" />
        <span>{{ formatScheduleRange(shared.start_time, shared.end_time) }}</span>
      </div>
      <div v-if="shared.location" class="meta-line">
        <van-icon name="location-o" />
        <span>{{ shared.location }}</span>
      </div>
      <div v-if="shared.remark" class="remark-block">{{ shared.remark }}</div>
      <div class="share-source">来源：{{ shared.source === "ai_parsed" ? "AI 解析后确认" : "手动创建" }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { fetchSharedSchedule, type ShareScheduleDto } from "@/api/share";
import { formatScheduleRange } from "@/utils/schedule-time";

const route = useRoute();
const shareUuid = String(route.params.shareUuid ?? "");
const loading = ref(true);
const shared = ref<ShareScheduleDto | null>(null);
const errorMessage = ref<string | null>(null);

onMounted(async () => {
  try {
    shared.value = await fetchSharedSchedule(shareUuid);
  } catch (error) {
    errorMessage.value = formatError(error, "当前分享链接无效，或对应内容已不可用。");
  } finally {
    loading.value = false;
  }
});

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
.public-share {
  min-height: 100vh;
  padding: var(--spacing-lg);
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 35%),
    linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}

.panel {
  max-width: 720px;
  margin: 0 auto;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.panel-title {
  margin: 0;
}

.panel-subtitle {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.preview-panel {
  background: rgba(255, 255, 255, 0.96);
}

.share-meta {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-bottom: var(--spacing-md);
  font-family: var(--font-family-mono);
}

.share-title {
  margin: 0 0 var(--spacing-md);
  font-size: clamp(28px, 5vw, 42px);
  line-height: 1.2;
}

.meta-line {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.remark-block {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-app);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  line-height: 1.7;
}

.share-source {
  margin-top: var(--spacing-md);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.error-panel {
  border-color: rgba(220, 38, 38, 0.18);
}
</style>
