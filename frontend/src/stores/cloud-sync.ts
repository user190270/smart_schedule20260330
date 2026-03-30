import { defineStore } from "pinia";

import { fetchHealth } from "@/api/client";
import { rebuildAllScheduleChunks, type RagChunkBuildAllResponse } from "@/api/rag";
import type { ScheduleRead } from "@/api/schedules";
import { fetchSyncStatus, pullSchedules, pushSchedules, type SyncStatusResponse } from "@/api/sync";
import { getJsonValue, setJsonValue } from "@/services/local-store";
import { useAuthStore } from "@/stores/auth";
import { useLocalScheduleStore } from "@/stores/local-schedules";

const DEVICE_META_KEY = "sync:device_meta";
const SCHEDULE_CACHE_KEY = "sync:schedule_cache";

type ActionStatus = "idle" | "success" | "failure";
type HealthStatus = "unknown" | "connected" | "failed";

type SyncActionState = {
  status: ActionStatus;
  message: string | null;
  at: string | null;
};

type DeviceMeta = {
  lastPushAt: string | null;
  lastPullAt: string | null;
  lastPushMessage: string | null;
  lastPullMessage: string | null;
};

function defaultMeta(): DeviceMeta {
  return {
    lastPushAt: null,
    lastPullAt: null,
    lastPushMessage: null,
    lastPullMessage: null
  };
}

function defaultActionState(): SyncActionState {
  return {
    status: "idle",
    message: null,
    at: null
  };
}

function formatApiError(error: unknown, fallback: string): string {
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

function summarizeLocalPending(localStore: ReturnType<typeof useLocalScheduleStore>): string {
  return [
    `待上传新增 ${localStore.pendingCreateCount} 条`,
    `待上传更新 ${localStore.pendingUpdateCount} 条`,
    `待删除云端 ${localStore.pendingDeleteCloudCount} 条`,
    `同步冲突 ${localStore.conflictCount} 条`
  ].join("，");
}

export const useCloudSyncStore = defineStore("cloud-sync", {
  state: () => ({
    initialized: false,
    healthStatus: "unknown" as HealthStatus,
    healthMessage: null as string | null,
    status: null as SyncStatusResponse | null,
    deviceMeta: defaultMeta(),
    cachedScheduleCount: 0,
    pushAction: defaultActionState(),
    pullAction: defaultActionState(),
    rebuildAction: defaultActionState()
  }),
  getters: {
    hasSuccessfulRebuild: (state) => state.status?.last_knowledge_rebuild_status === "success"
  },
  actions: {
    async initialize(force = false) {
      if (this.initialized && !force) {
        return;
      }

      await this.loadDeviceMeta();
      await this.loadCachedScheduleCount();
      this.initialized = true;

      const authStore = useAuthStore();
      await this.checkHealth();
      if (authStore.isAuthenticated) {
        await this.refreshStatus().catch(() => undefined);
      }
    },

    async loadDeviceMeta() {
      this.deviceMeta = (await getJsonValue<DeviceMeta>(DEVICE_META_KEY)) ?? defaultMeta();
    },

    async persistDeviceMeta() {
      await setJsonValue(DEVICE_META_KEY, this.deviceMeta);
    },

    async loadCachedScheduleCount() {
      const cached = (await getJsonValue<ScheduleRead[]>(SCHEDULE_CACHE_KEY)) ?? [];
      this.cachedScheduleCount = cached.filter((record) => !record.is_deleted).length;
    },

    async getCachedSchedules(): Promise<ScheduleRead[]> {
      const cached = await getJsonValue<ScheduleRead[]>(SCHEDULE_CACHE_KEY);
      return cached ?? [];
    },

    async replaceScheduleCache(records: ScheduleRead[]) {
      await setJsonValue(SCHEDULE_CACHE_KEY, records);
      this.cachedScheduleCount = records.filter((record) => !record.is_deleted).length;
    },

    async clearScheduleCache() {
      await this.replaceScheduleCache([]);
    },

    async checkHealth() {
      try {
        const result = await fetchHealth();
        this.healthStatus = result.status === "ok" ? "connected" : "failed";
        this.healthMessage = result.status === "ok" ? "云端 API 连接正常。" : `云端健康检查返回状态：${result.status}`;
      } catch (error) {
        this.healthStatus = "failed";
        this.healthMessage = formatApiError(error, "无法连接云端 API。");
      }
    },

    async refreshStatus() {
      const authStore = useAuthStore();
      if (!authStore.isAuthenticated) {
        this.status = null;
        return null;
      }

      try {
        this.status = await fetchSyncStatus();
        this.healthStatus = "connected";
        return this.status;
      } catch (error) {
        this.healthStatus = "failed";
        this.healthMessage = formatApiError(error, "读取云端状态失败。");
        throw error;
      }
    },

    async runPush() {
      const authStore = useAuthStore();
      const localScheduleStore = useLocalScheduleStore();
      await localScheduleStore.initialize();

      const plan = await localScheduleStore.buildPushPlan();
      if (plan.records.length === 0) {
        const at = new Date().toISOString();
        const message = `没有需要 Push 的改动。${summarizeLocalPending(localScheduleStore)}。`;
        this.deviceMeta.lastPushAt = at;
        this.deviceMeta.lastPushMessage = message;
        await this.persistDeviceMeta();
        this.pushAction = { status: "success", message, at };
        return { results: [] };
      }

      try {
        const response = await pushSchedules(plan.records);
        await localScheduleStore.applyPushResults(plan.localIds, response.results);

        if (authStore.user && response.results.some((item) => item.status === "ignored")) {
          const pullResponse = await pullSchedules();
          await this.replaceScheduleCache(pullResponse.records);
          await localScheduleStore.mergePulledSchedules(pullResponse.records, authStore.user.id);
        }

        const at = new Date().toISOString();
        const created = response.results.filter((item) => item.status === "created").length;
        const updated = response.results.filter((item) => item.status === "updated").length;
        const ignored = response.results.filter((item) => item.status === "ignored").length;
        const message = `Push 完成：新增 ${created} 条，更新 ${updated} 条，忽略 ${ignored} 条。`;

        this.deviceMeta.lastPushAt = at;
        this.deviceMeta.lastPushMessage = message;
        await this.persistDeviceMeta();
        this.pushAction = { status: "success", message, at };
        await this.refreshStatus().catch(() => undefined);
        return response;
      } catch (error) {
        const message = formatApiError(error, "Push 失败。");
        this.pushAction = { status: "failure", message, at: new Date().toISOString() };
        throw new Error(message);
      }
    },

    async runPull() {
      const authStore = useAuthStore();
      const localScheduleStore = useLocalScheduleStore();
      await localScheduleStore.initialize();
      if (!authStore.user) {
        throw new Error("请先登录后再执行 Pull。");
      }

      try {
        const response = await pullSchedules();
        await this.replaceScheduleCache(response.records);
        const merged = await localScheduleStore.mergePulledSchedules(response.records, authStore.user.id);

        const at = new Date().toISOString();
        const activeCloudCount = response.records.filter((record) => !record.is_deleted).length;
        const message = `Pull 完成：合并了 ${activeCloudCount} 条云端日程，本地当前可见 ${merged.length} 条。`;

        this.deviceMeta.lastPullAt = at;
        this.deviceMeta.lastPullMessage = message;
        await this.persistDeviceMeta();
        this.pullAction = { status: "success", message, at };
        await this.refreshStatus().catch(() => undefined);
        return { records: response.records };
      } catch (error) {
        const message = formatApiError(error, "Pull 失败。");
        this.pullAction = { status: "failure", message, at: new Date().toISOString() };
        throw new Error(message);
      }
    },

    async runRebuildKnowledgeBase(chunkSize = 120): Promise<RagChunkBuildAllResponse> {
      try {
        const response = await rebuildAllScheduleChunks(chunkSize);
        this.rebuildAction = {
          status: "success",
          message: response.message,
          at: response.rebuilt_at
        };
        await this.refreshStatus().catch(() => undefined);
        return response;
      } catch (error) {
        const message = formatApiError(error, "重建知识库失败。");
        this.rebuildAction = { status: "failure", message, at: new Date().toISOString() };
        await this.refreshStatus().catch(() => undefined);
        throw new Error(message);
      }
    },

    clearCloudStatus() {
      this.status = null;
      this.healthMessage = null;
      this.pushAction = defaultActionState();
      this.pullAction = defaultActionState();
      this.rebuildAction = defaultActionState();
      void this.clearScheduleCache();
    }
  }
});
