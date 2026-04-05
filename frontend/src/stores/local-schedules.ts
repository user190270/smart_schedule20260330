import { defineStore } from "pinia";

import type { ScheduleRead, ScheduleSource } from "@/api/schedules";
import type { SyncPushResultItem, SyncScheduleRecord } from "@/api/sync";
import {
  buildNewLocalScheduleRecord,
  buildPulledCloudRecord,
  createConflictSnapshotFromCloud,
  detectLocalScheduleStorageKind,
  readLocalScheduleRecords,
  sortLocalScheduleRecords,
  writeLocalScheduleRecords,
  type ConflictSnapshot,
  type LocalScheduleRecord,
  type LocalScheduleScope,
  type ScheduleStorageStrategy,
  type ScheduleSyncIntent
} from "@/repositories/local-schedules";
import type { StoreKind } from "@/services/local-store";

type EditableScheduleInput = {
  title: string;
  start_time: string;
  end_time: string | null;
  location?: string | null;
  remark?: string | null;
  source?: ScheduleSource;
  storage_strategy?: ScheduleStorageStrategy;
};

type PushPlan = {
  localIds: string[];
  records: SyncScheduleRecord[];
};

type TagTone = "primary" | "success" | "warning" | "danger";

export type ScheduleTag = {
  label: string;
  type: TagTone;
};

export type DeleteActionOption = {
  key: "delete_local" | "delete_cloud_keep_local" | "delete_both";
  label: string;
  description: string;
  confirmTitle: string;
  confirmMessage: string;
};

export type ConflictResolutionAction = "accept_cloud" | "keep_local";

export type ConflictDetails = {
  local_id: string;
  title: string;
  reason: string;
  local_updated_at: string;
  cloud_updated_at: string | null;
  local_version: ConflictSnapshot;
  cloud_version: ConflictSnapshot | null;
};

function nowIso(): string {
  return new Date().toISOString();
}

function cloneRecord(record: LocalScheduleRecord): LocalScheduleRecord {
  return {
    ...record,
    conflict_snapshot: record.conflict_snapshot ? { ...record.conflict_snapshot } : null
  };
}

function cloneRecords(records: LocalScheduleRecord[]): LocalScheduleRecord[] {
  return records.map(cloneRecord);
}

function sanitizeStrategy(strategy: ScheduleStorageStrategy | undefined): ScheduleStorageStrategy {
  return strategy ?? "local_only";
}

function strategyAllowsKnowledge(strategy: ScheduleStorageStrategy): boolean {
  return strategy === "sync_to_cloud_and_knowledge";
}

function strategyFromKnowledgeFlag(allowRagIndexing: boolean): ScheduleStorageStrategy {
  return allowRagIndexing ? "sync_to_cloud_and_knowledge" : "sync_to_cloud";
}

function hasEditableChanges(previous: LocalScheduleRecord, input: EditableScheduleInput, nextStrategy: ScheduleStorageStrategy) {
  return (
    previous.title !== input.title ||
    previous.start_time !== input.start_time ||
    previous.end_time !== input.end_time ||
    previous.location !== (input.location ?? null) ||
    previous.remark !== (input.remark ?? null) ||
    previous.source !== (input.source ?? previous.source) ||
    previous.storage_strategy !== nextStrategy
  );
}

function syncIntentLabel(intent: ScheduleSyncIntent): string {
  switch (intent) {
    case "pending_create":
      return "待上传新增";
    case "pending_update":
      return "待上传更新";
    case "pending_delete_cloud":
      return "待删除云端";
    case "conflict":
      return "同步冲突";
    default:
      return "已同步";
  }
}

function storageStrategyLabel(strategy: ScheduleStorageStrategy): string {
  switch (strategy) {
    case "sync_to_cloud":
      return "同步到云端";
    case "sync_to_cloud_and_knowledge":
      return "同步到云端并纳入知识库";
    default:
      return "仅本地";
  }
}

function presenceTags(record: LocalScheduleRecord): ScheduleTag[] {
  const tags: ScheduleTag[] = [];
  if (record.presence === "local_only" || record.presence === "local_and_cloud") {
    tags.push({ label: "本地", type: "success" });
  }
  if (record.presence === "cloud_only" || record.presence === "local_and_cloud") {
    tags.push({ label: "云端", type: "primary" });
  }
  return tags;
}

function toPushRecord(record: LocalScheduleRecord): SyncScheduleRecord {
  return {
    id: record.cloud_schedule_id,
    title: record.title,
    start_time: record.start_time,
    end_time: record.end_time,
    location: record.location,
    remark: record.remark,
    source: record.source,
    updated_at: record.updated_at,
    allow_rag_indexing: strategyAllowsKnowledge(record.storage_strategy),
    is_deleted: record.sync_intent === "pending_delete_cloud"
  };
}

function clearConflictState(record: LocalScheduleRecord) {
  record.conflict_reason = null;
  record.conflict_snapshot = null;
}

function snapshotFromRecord(record: LocalScheduleRecord): ConflictSnapshot {
  return {
    title: record.title,
    start_time: record.start_time,
    end_time: record.end_time,
    location: record.location,
    remark: record.remark,
    source: record.source,
    updated_at: record.updated_at,
    allow_rag_indexing: record.allow_rag_indexing
  };
}

function setConflictState(
  record: LocalScheduleRecord,
  reason: string,
  currentUserId: number | null,
  cloudSnapshot?: ConflictSnapshot | null
) {
  record.sync_intent = "conflict";
  record.conflict_reason = reason;
  record.conflict_snapshot = cloudSnapshot ? { ...cloudSnapshot } : record.conflict_snapshot;
  if (cloudSnapshot) {
    record.cloud_updated_at = cloudSnapshot.updated_at;
    record.allow_rag_indexing = cloudSnapshot.allow_rag_indexing;
    record.presence = "local_and_cloud";
  }
  if (currentUserId !== null && record.cloud_schedule_id !== null) {
    record.cloud_user_id = currentUserId;
  }
}

function updateCloudBackedRecordFromServer(localRecord: LocalScheduleRecord, cloudRecord: ScheduleRead, cloudUserId: number) {
  localRecord.cloud_schedule_id = cloudRecord.id;
  localRecord.cloud_user_id = cloudUserId;
  localRecord.title = cloudRecord.title;
  localRecord.start_time = cloudRecord.start_time;
  localRecord.end_time = cloudRecord.end_time;
  localRecord.location = cloudRecord.location;
  localRecord.remark = cloudRecord.remark;
  localRecord.source = cloudRecord.source;
  localRecord.updated_at = cloudRecord.updated_at;
  localRecord.cloud_updated_at = cloudRecord.updated_at;
  localRecord.allow_rag_indexing = cloudRecord.allow_rag_indexing;
  localRecord.presence = "local_and_cloud";
  localRecord.sync_intent = "synced";
  localRecord.is_deleted = false;
  localRecord.remove_local_after_push = false;
  localRecord.storage_strategy = strategyFromKnowledgeFlag(cloudRecord.allow_rag_indexing);
  clearConflictState(localRecord);
}

function reconcileMissingCloudRecord(localRecord: LocalScheduleRecord) {
  localRecord.cloud_schedule_id = null;
  localRecord.cloud_user_id = null;
  localRecord.cloud_updated_at = null;
  localRecord.allow_rag_indexing = strategyAllowsKnowledge(localRecord.storage_strategy);
  localRecord.presence = "local_only";
  localRecord.sync_intent = localRecord.storage_strategy === "local_only" ? "synced" : "pending_create";
  localRecord.is_deleted = false;
  localRecord.remove_local_after_push = false;
  clearConflictState(localRecord);
}

function resolveAccountScope(record: LocalScheduleRecord, currentAccountId: number | null): LocalScheduleScope {
  if (record.cloud_schedule_id === null) {
    return "device_local";
  }
  if (currentAccountId === null) {
    return "device_local";
  }
  if (record.cloud_user_id === currentAccountId) {
    return "current_account_bound";
  }
  return "other_account_bound";
}

function isVisibleForCurrentAccount(record: LocalScheduleRecord, currentAccountId: number | null): boolean {
  if (record.is_deleted) {
    return false;
  }
  if (currentAccountId === null) {
    return true;
  }
  return resolveAccountScope(record, currentAccountId) !== "other_account_bound";
}

export const useLocalScheduleStore = defineStore("local-schedules", {
  state: () => ({
    initialized: false,
    storageKind: "web" as StoreKind,
    currentAccountId: null as number | null,
    records: [] as LocalScheduleRecord[]
  }),
  getters: {
    visibleRecords(state): LocalScheduleRecord[] {
      return sortLocalScheduleRecords(state.records.filter((record) => isVisibleForCurrentAccount(record, state.currentAccountId)));
    },
    hiddenOtherAccountCount(state): number {
      if (state.currentAccountId === null) {
        return 0;
      }
      return state.records.filter((record) => resolveAccountScope(record, state.currentAccountId) === "other_account_bound").length;
    },
    activeCount(): number {
      return this.visibleRecords.length;
    },
    localOnlyCount(): number {
      return this.visibleRecords.filter((record) => record.presence === "local_only").length;
    },
    cloudBackedCount(): number {
      return this.visibleRecords.filter((record) => record.cloud_schedule_id !== null).length;
    },
    pendingCreateCount(): number {
      return this.visibleRecords.filter((record) => record.sync_intent === "pending_create").length;
    },
    pendingUpdateCount(): number {
      return this.visibleRecords.filter((record) => record.sync_intent === "pending_update").length;
    },
    pendingDeleteCloudCount(): number {
      return this.visibleRecords.filter((record) => record.sync_intent === "pending_delete_cloud").length;
    },
    conflictCount(): number {
      return this.visibleRecords.filter((record) => record.sync_intent === "conflict").length;
    },
    pendingPushCount(): number {
      return this.pendingCreateCount + this.pendingUpdateCount + this.pendingDeleteCloudCount;
    },
    shareableRecords(): LocalScheduleRecord[] {
      return this.visibleRecords.filter(
        (record) => record.cloud_schedule_id !== null && record.sync_intent !== "pending_delete_cloud"
      );
    }
  },
  actions: {
    async initialize(force = false) {
      if (this.initialized && !force) {
        return;
      }
      this.storageKind = await detectLocalScheduleStorageKind();
      this.records = await readLocalScheduleRecords();
      this.initialized = true;
    },

    async persist(records: LocalScheduleRecord[]) {
      this.records = records;
      this.storageKind = await writeLocalScheduleRecords(records);
      this.initialized = true;
    },

    async reload() {
      await this.initialize(true);
    },

    async setCurrentAccount(userId: number | null) {
      await this.initialize();
      this.currentAccountId = userId;

      const next = cloneRecords(this.records);
      let changed = false;

      next.forEach((record) => {
        if (record.cloud_schedule_id === null && record.cloud_user_id !== null) {
          record.cloud_user_id = null;
          changed = true;
        }
      });

      if (changed) {
        await this.persist(next);
        return;
      }

      this.records = next;
    },

    getAccountScope(record: LocalScheduleRecord): LocalScheduleScope {
      return resolveAccountScope(record, this.currentAccountId);
    },

    async createSchedule(input: EditableScheduleInput) {
      await this.initialize();
      const storageStrategy = sanitizeStrategy(input.storage_strategy);
      const next = [
        buildNewLocalScheduleRecord({
          title: input.title,
          start_time: input.start_time,
          end_time: input.end_time,
          location: input.location ?? null,
          remark: input.remark ?? null,
          source: input.source,
          storage_strategy: storageStrategy
        }),
        ...cloneRecords(this.records)
      ];
      await this.persist(next);
      return next[0];
    },

    async updateSchedule(localId: string, input: EditableScheduleInput) {
      await this.initialize();
      const next = cloneRecords(this.records);
      const target = next.find((record) => record.local_id === localId);
      if (!target) {
        throw new Error("未找到要编辑的本地日程。");
      }

      const nextStrategy = sanitizeStrategy(input.storage_strategy ?? target.storage_strategy);
      const changed = hasEditableChanges(target, input, nextStrategy);

      target.title = input.title;
      target.start_time = input.start_time;
      target.end_time = input.end_time;
      target.location = input.location ?? null;
      target.remark = input.remark ?? null;
      target.source = input.source ?? target.source;
      target.storage_strategy = nextStrategy;
      target.allow_rag_indexing = strategyAllowsKnowledge(nextStrategy);
      target.updated_at = nowIso();
      target.is_deleted = false;
      target.remove_local_after_push = false;
      clearConflictState(target);

      if (target.cloud_schedule_id === null) {
        target.cloud_user_id = null;
        target.presence = "local_only";
        target.sync_intent = nextStrategy === "local_only" ? "synced" : "pending_create";
      } else if (nextStrategy === "local_only") {
        target.presence = "local_and_cloud";
        target.sync_intent = "pending_delete_cloud";
      } else {
        target.presence = "local_and_cloud";
        target.sync_intent = changed ? "pending_update" : "synced";
      }

      await this.persist(next);
      return target;
    },

    async mergePulledSchedules(cloudRecords: ScheduleRead[], currentUserId: number) {
      await this.initialize();
      this.currentAccountId = currentUserId;

      const next = cloneRecords(this.records);
      const localByCloudId = new Map<number, LocalScheduleRecord>();
      const pulledCloudIds = new Set<number>();

      for (const record of next) {
        if (record.cloud_schedule_id === null) {
          continue;
        }
        if (record.cloud_user_id !== null && record.cloud_user_id !== currentUserId) {
          continue;
        }
        localByCloudId.set(record.cloud_schedule_id, record);
      }

      for (const cloudRecord of cloudRecords) {
        pulledCloudIds.add(cloudRecord.id);
        const localRecord = localByCloudId.get(cloudRecord.id);
        const cloudSnapshot = createConflictSnapshotFromCloud(cloudRecord);

        if (cloudRecord.is_deleted) {
          if (!localRecord) {
            continue;
          }
          if (localRecord.remove_local_after_push || localRecord.is_deleted) {
            const index = next.findIndex((item) => item.local_id === localRecord.local_id);
            if (index >= 0) {
              next.splice(index, 1);
            }
            continue;
          }
          localRecord.cloud_schedule_id = null;
          localRecord.cloud_user_id = null;
          localRecord.cloud_updated_at = null;
          localRecord.allow_rag_indexing = false;
          localRecord.presence = "local_only";
          localRecord.storage_strategy = "local_only";
          localRecord.sync_intent = localRecord.sync_intent === "conflict" ? "conflict" : "synced";
          clearConflictState(localRecord);
          continue;
        }

        if (!localRecord) {
          next.unshift(buildPulledCloudRecord(cloudRecord, currentUserId));
          continue;
        }

        localRecord.cloud_user_id = currentUserId;

        if (localRecord.sync_intent === "pending_update") {
          if (localRecord.cloud_updated_at && cloudRecord.updated_at > localRecord.cloud_updated_at) {
            setConflictState(
              localRecord,
              "云端版本在你本地修改后也发生了更新，请选择保留哪一边。",
              currentUserId,
              cloudSnapshot
            );
          }
          continue;
        }

        if (localRecord.sync_intent === "pending_delete_cloud") {
          continue;
        }

        if (localRecord.sync_intent === "conflict") {
          setConflictState(localRecord, localRecord.conflict_reason ?? "本地与云端版本不一致。", currentUserId, cloudSnapshot);
          continue;
        }

        updateCloudBackedRecordFromServer(localRecord, cloudRecord, currentUserId);
      }

      for (const localRecord of next) {
        if (localRecord.cloud_schedule_id === null) {
          continue;
        }
        if (localRecord.is_deleted) {
          continue;
        }
        if (localRecord.cloud_user_id !== null && localRecord.cloud_user_id !== currentUserId) {
          continue;
        }
        if (pulledCloudIds.has(localRecord.cloud_schedule_id)) {
          continue;
        }
        reconcileMissingCloudRecord(localRecord);
      }

      await this.persist(next);
      return this.visibleRecords;
    },

    async deleteLocalCopy(localId: string) {
      await this.initialize();
      const next = this.records.filter((record) => record.local_id !== localId);
      await this.persist(next);
    },

    async markDeleteCloud(localId: string, removeLocalAfterPush = false) {
      await this.initialize();
      const next = cloneRecords(this.records);
      const target = next.find((record) => record.local_id === localId);
      if (!target || target.cloud_schedule_id === null) {
        throw new Error("只有已经存在云端副本的日程才能标记删除云端。");
      }

      target.updated_at = nowIso();
      target.sync_intent = "pending_delete_cloud";
      target.storage_strategy = "local_only";
      target.allow_rag_indexing = false;
      target.remove_local_after_push = removeLocalAfterPush;
      clearConflictState(target);

      if (removeLocalAfterPush) {
        target.is_deleted = true;
      } else {
        target.is_deleted = false;
        target.presence = "local_and_cloud";
      }

      await this.persist(next);
      return target;
    },

    async buildPushPlan(): Promise<PushPlan> {
      await this.initialize();
      const currentUserId = this.currentAccountId;
      if (currentUserId === null) {
        return { localIds: [], records: [] };
      }

      const pushable = this.records.filter((record) => {
        const scope = resolveAccountScope(record, currentUserId);
        if (scope === "other_account_bound") {
          return false;
        }
        if (record.sync_intent === "conflict") {
          return false;
        }
        if (record.sync_intent === "pending_create" || record.sync_intent === "pending_update") {
          return true;
        }
        return record.sync_intent === "pending_delete_cloud" && record.cloud_schedule_id !== null;
      });

      return {
        localIds: pushable.map((record) => record.local_id),
        records: pushable.map(toPushRecord)
      };
    },

    async applyPushResults(localIds: string[], results: SyncPushResultItem[]) {
      await this.initialize();
      const next = cloneRecords(this.records);

      localIds.forEach((localId, index) => {
        const result = results[index];
        const target = next.find((record) => record.local_id === localId);
        if (!target || !result) {
          return;
        }

        if (target.sync_intent === "pending_delete_cloud") {
          if (result.status === "updated") {
            if (target.remove_local_after_push || target.is_deleted) {
              const targetIndex = next.findIndex((item) => item.local_id === target.local_id);
              if (targetIndex >= 0) {
                next.splice(targetIndex, 1);
              }
              return;
            }

            target.cloud_schedule_id = null;
            target.cloud_user_id = null;
            target.cloud_updated_at = null;
            target.presence = "local_only";
            target.sync_intent = "synced";
            target.storage_strategy = "local_only";
            target.allow_rag_indexing = false;
            target.is_deleted = false;
            target.remove_local_after_push = false;
            clearConflictState(target);
            return;
          }

          setConflictState(
            target,
            result.reason ?? "云端删除未成功，请先检查云端版本后再决定如何处理。",
            this.currentAccountId
          );
          target.is_deleted = false;
          target.remove_local_after_push = false;
          return;
        }

        if (result.status === "ignored") {
          setConflictState(
            target,
            result.reason ?? "本地版本并不比云端新，请选择采用云端还是保留本地覆盖云端。",
            this.currentAccountId
          );
          return;
        }

        target.cloud_schedule_id = result.schedule_id;
        target.cloud_user_id = this.currentAccountId;
        target.cloud_updated_at = target.updated_at;
        target.presence = "local_and_cloud";
        target.sync_intent = "synced";
        target.allow_rag_indexing = strategyAllowsKnowledge(target.storage_strategy);
        target.is_deleted = false;
        target.remove_local_after_push = false;
        if (target.storage_strategy === "local_only") {
          target.storage_strategy = "sync_to_cloud";
        }
        clearConflictState(target);
      });

      await this.persist(next);
    },

    getRecordByLocalId(localId: string): LocalScheduleRecord | null {
      return this.records.find((record) => record.local_id === localId) ?? null;
    },

    getDeleteOptions(record: LocalScheduleRecord): DeleteActionOption[] {
      if (record.cloud_schedule_id === null) {
        return [
          {
            key: "delete_local",
            label: "删除本地",
            description: "只删除当前设备中的本地副本，不涉及任何云端数据。",
            confirmTitle: "删除本地日程",
            confirmMessage: "确认删除这条本地日程吗？此操作会移除当前设备中的记录。"
          }
        ];
      }

      return [
        {
          key: "delete_local",
          label: "仅删除本地副本",
          description: "不会删除云端记录。如果以后执行 Pull，这条云端日程会重新出现在本地。",
          confirmTitle: "仅删除本地副本",
          confirmMessage: "确认只删除本地副本吗？云端记录会保留，后续 Pull 仍可能把它重新拉回本地。"
        },
        {
          key: "delete_cloud_keep_local",
          label: "从云端删除，保留本地副本",
          description: "本地会先保留，并进入“待删除云端”状态。下次 Push 时才会真正删除云端。",
          confirmTitle: "从云端删除，保留本地副本",
          confirmMessage: "确认把这条日程标记为“待删除云端”吗？Push 成功后，云端副本会删除，但本地副本会继续保留。"
        },
        {
          key: "delete_both",
          label: "同时删除本地与云端",
          description: "本地会先隐藏，并在下次 Push 时删除云端，完成后两端都不再保留这条日程。",
          confirmTitle: "同时删除本地与云端",
          confirmMessage: "确认同时删除本地与云端吗？Push 成功后，这条日程会从两端都移除。"
        }
      ];
    },

    async applyDeleteAction(localId: string, action: DeleteActionOption["key"]) {
      if (action === "delete_local") {
        await this.deleteLocalCopy(localId);
        return;
      }
      if (action === "delete_cloud_keep_local") {
        await this.markDeleteCloud(localId, false);
        return;
      }
      await this.markDeleteCloud(localId, true);
    },

    getConflictDetails(localId: string): ConflictDetails | null {
      const record = this.getRecordByLocalId(localId);
      if (!record || record.sync_intent !== "conflict") {
        return null;
      }

      return {
        local_id: record.local_id,
        title: record.title,
        reason: record.conflict_reason ?? "本地与云端版本不一致，请选择要保留的版本。",
        local_updated_at: record.updated_at,
        cloud_updated_at: record.cloud_updated_at,
        local_version: snapshotFromRecord(record),
        cloud_version: record.conflict_snapshot ? { ...record.conflict_snapshot } : null
      };
    },

    async resolveConflict(localId: string, action: ConflictResolutionAction) {
      await this.initialize();
      const next = cloneRecords(this.records);
      const target = next.find((record) => record.local_id === localId);
      if (!target || target.sync_intent !== "conflict") {
        throw new Error("当前记录不是可解决的同步冲突状态。");
      }

      if (action === "accept_cloud") {
        if (!target.conflict_snapshot) {
          throw new Error("当前缺少云端版本快照。请先执行 Pull 刷新冲突信息。");
        }

        target.title = target.conflict_snapshot.title;
        target.start_time = target.conflict_snapshot.start_time;
        target.end_time = target.conflict_snapshot.end_time;
        target.location = target.conflict_snapshot.location;
        target.remark = target.conflict_snapshot.remark;
        target.source = target.conflict_snapshot.source;
        target.updated_at = target.conflict_snapshot.updated_at;
        target.cloud_updated_at = target.conflict_snapshot.updated_at;
        target.allow_rag_indexing = target.conflict_snapshot.allow_rag_indexing;
        target.storage_strategy = strategyFromKnowledgeFlag(target.conflict_snapshot.allow_rag_indexing);
        target.sync_intent = "synced";
        target.presence = "local_and_cloud";
        target.is_deleted = false;
        target.remove_local_after_push = false;
        if (this.currentAccountId !== null) {
          target.cloud_user_id = this.currentAccountId;
        }
        clearConflictState(target);
      } else {
        target.updated_at = nowIso();
        target.sync_intent = "pending_update";
        target.presence = "local_and_cloud";
        target.is_deleted = false;
        target.remove_local_after_push = false;
        if (this.currentAccountId !== null && target.cloud_schedule_id !== null) {
          target.cloud_user_id = this.currentAccountId;
        }
        if (target.conflict_snapshot) {
          target.cloud_updated_at = target.conflict_snapshot.updated_at;
          target.allow_rag_indexing = strategyAllowsKnowledge(target.storage_strategy);
        }
        clearConflictState(target);
      }

      await this.persist(next);
      return target;
    },

    describeTags(record: LocalScheduleRecord): ScheduleTag[] {
      const tags = presenceTags(record);

      if (record.sync_intent === "pending_create") {
        tags.push({ label: "待上传新增", type: "warning" });
      } else if (record.sync_intent === "pending_update") {
        tags.push({ label: "待上传更新", type: "warning" });
      } else if (record.sync_intent === "pending_delete_cloud") {
        tags.push({ label: "待删除云端", type: "danger" });
      } else if (record.sync_intent === "conflict") {
        tags.push({ label: "同步冲突", type: "danger" });
      } else {
        tags.push({ label: "已同步", type: "primary" });
      }

      tags.push({
        label: storageStrategyLabel(record.storage_strategy),
        type: record.storage_strategy === "local_only" ? "success" : "primary"
      });

      return tags;
    },

    describePresence(record: LocalScheduleRecord): ScheduleTag[] {
      return presenceTags(record);
    },

    syncStateLabel(intent: ScheduleSyncIntent): string {
      return syncIntentLabel(intent);
    },

    storageStrategyLabel(strategy: ScheduleStorageStrategy): string {
      return storageStrategyLabel(strategy);
    },

    presenceFilterMatches(record: LocalScheduleRecord, filter: "all" | "local" | "cloud"): boolean {
      if (filter === "all") {
        return true;
      }
      if (filter === "local") {
        return record.presence === "local_only" || record.presence === "local_and_cloud";
      }
      return record.presence === "cloud_only" || record.presence === "local_and_cloud";
    },

    storageStrategyOptions(): { label: string; value: ScheduleStorageStrategy; hint: string }[] {
      return [
        {
          label: "仅本地",
          value: "local_only",
          hint: "只保存在本地仓，不会进入云端，也不会进入知识库。"
        },
        {
          label: "同步到云端",
          value: "sync_to_cloud",
          hint: "Push 后会进入云端，但默认不纳入知识库。"
        },
        {
          label: "同步到云端并纳入知识库",
          value: "sync_to_cloud_and_knowledge",
          hint: "Push 后进入云端，并在重建知识库时参与索引。"
        }
      ];
    }
  }
});
