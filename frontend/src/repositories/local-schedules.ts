import type { ScheduleRead, ScheduleSource } from "@/api/schedules";
import type { StoreKind } from "@/services/local-store";
import { getJsonValue, getStorageBackendKind, setJsonValue } from "@/services/local-store";

const LOCAL_SCHEDULES_KEY = "schedules:local_records:v2";

export type SchedulePresence = "local_only" | "cloud_only" | "local_and_cloud";
export type ScheduleSyncIntent =
  | "synced"
  | "pending_create"
  | "pending_update"
  | "pending_delete_cloud"
  | "conflict";
export type ScheduleStorageStrategy = "local_only" | "sync_to_cloud" | "sync_to_cloud_and_knowledge";
export type LocalScheduleScope = "device_local" | "current_account_bound" | "other_account_bound";

export type ConflictSnapshot = {
  title: string;
  start_time: string;
  end_time: string | null;
  location: string | null;
  remark: string | null;
  source: ScheduleSource;
  updated_at: string;
  allow_rag_indexing: boolean;
};

export type LocalScheduleRecord = {
  local_id: string;
  cloud_schedule_id: number | null;
  cloud_user_id: number | null;
  title: string;
  start_time: string;
  end_time: string | null;
  location: string | null;
  remark: string | null;
  source: ScheduleSource;
  updated_at: string;
  cloud_updated_at: string | null;
  allow_rag_indexing: boolean;
  is_deleted: boolean;
  presence: SchedulePresence;
  sync_intent: ScheduleSyncIntent;
  storage_strategy: ScheduleStorageStrategy;
  remove_local_after_push: boolean;
  conflict_reason: string | null;
  conflict_snapshot: ConflictSnapshot | null;
};

type LocalScheduleCollection = {
  version: 3;
  records: LocalScheduleRecord[];
};

export type LocalScheduleDraft = {
  title: string;
  start_time: string;
  end_time: string | null;
  location?: string | null;
  remark?: string | null;
  source?: ScheduleSource;
  storage_strategy?: ScheduleStorageStrategy;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function asSource(value: unknown): ScheduleSource {
  return value === "ai_parsed" ? "ai_parsed" : "manual";
}

function asPresence(value: unknown): SchedulePresence {
  if (value === "local_only" || value === "cloud_only" || value === "local_and_cloud") {
    return value;
  }
  return "local_only";
}

function asSyncIntent(value: unknown, cloudScheduleId: number | null, isDeleted: boolean): ScheduleSyncIntent {
  if (
    value === "synced" ||
    value === "pending_create" ||
    value === "pending_update" ||
    value === "pending_delete_cloud" ||
    value === "conflict"
  ) {
    return value;
  }

  if (value === "clean") {
    return "synced";
  }
  if (value === "pending_push") {
    if (cloudScheduleId === null) {
      return "pending_create";
    }
    return isDeleted ? "pending_delete_cloud" : "pending_update";
  }
  return cloudScheduleId === null ? "pending_create" : "synced";
}

function asStorageStrategy(value: unknown, cloudScheduleId: number | null): ScheduleStorageStrategy {
  if (value === "local_only" || value === "sync_to_cloud" || value === "sync_to_cloud_and_knowledge") {
    return value;
  }
  return cloudScheduleId === null ? "local_only" : "sync_to_cloud";
}

function normalizeConflictSnapshot(value: unknown): ConflictSnapshot | null {
  if (!isObject(value)) {
    return null;
  }

  const title = typeof value.title === "string" ? value.title : null;
  const startTime = typeof value.start_time === "string" ? value.start_time : null;
  const updatedAt = typeof value.updated_at === "string" ? value.updated_at : null;

  if (!title || !startTime || !updatedAt) {
    return null;
  }

  return {
    title,
    start_time: startTime,
    end_time: asNullableString(value.end_time),
    location: asNullableString(value.location),
    remark: asNullableString(value.remark),
    source: asSource(value.source),
    updated_at: updatedAt,
    allow_rag_indexing: value.allow_rag_indexing === true
  };
}

function nowIso(): string {
  return new Date().toISOString();
}

function createLocalId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function normalizeRecord(value: unknown): LocalScheduleRecord | null {
  if (!isObject(value)) {
    return null;
  }

  const localId = typeof value.local_id === "string" ? value.local_id : null;
  const title = typeof value.title === "string" ? value.title : null;
  const startTime = typeof value.start_time === "string" ? value.start_time : null;
  const updatedAt = typeof value.updated_at === "string" ? value.updated_at : null;

  if (!localId || !title || !startTime || !updatedAt) {
    return null;
  }

  const cloudScheduleId = asNullableNumber(value.cloud_schedule_id);
  const isDeleted = value.is_deleted === true;

  return {
    local_id: localId,
    cloud_schedule_id: cloudScheduleId,
    cloud_user_id: asNullableNumber(value.cloud_user_id),
    title,
    start_time: startTime,
    end_time: asNullableString(value.end_time),
    location: asNullableString(value.location),
    remark: asNullableString(value.remark),
    source: asSource(value.source),
    updated_at: updatedAt,
    cloud_updated_at: asNullableString(value.cloud_updated_at),
    allow_rag_indexing: value.allow_rag_indexing === true,
    is_deleted: isDeleted,
    presence: asPresence(value.presence),
    sync_intent: asSyncIntent(value.sync_intent ?? value.sync_state, cloudScheduleId, isDeleted),
    storage_strategy: asStorageStrategy(value.storage_strategy, cloudScheduleId),
    remove_local_after_push: value.remove_local_after_push === true,
    conflict_reason: asNullableString(value.conflict_reason),
    conflict_snapshot: normalizeConflictSnapshot(value.conflict_snapshot)
  };
}

function normalizeCollection(raw: unknown): LocalScheduleRecord[] {
  if (Array.isArray(raw)) {
    return raw.map(normalizeRecord).filter((record): record is LocalScheduleRecord => record !== null);
  }

  if (!isObject(raw) || !Array.isArray(raw.records)) {
    return [];
  }

  return raw.records.map(normalizeRecord).filter((record): record is LocalScheduleRecord => record !== null);
}

export async function detectLocalScheduleStorageKind(): Promise<StoreKind> {
  return getStorageBackendKind();
}

export async function readLocalScheduleRecords(): Promise<LocalScheduleRecord[]> {
  const raw = await getJsonValue<LocalScheduleCollection | LocalScheduleRecord[]>(LOCAL_SCHEDULES_KEY);
  return normalizeCollection(raw);
}

export async function writeLocalScheduleRecords(records: LocalScheduleRecord[]): Promise<StoreKind> {
  return setJsonValue(LOCAL_SCHEDULES_KEY, {
    version: 3,
    records
  });
}

export function getInitialSyncIntent(strategy: ScheduleStorageStrategy): ScheduleSyncIntent {
  return strategy === "local_only" ? "synced" : "pending_create";
}

export function createConflictSnapshotFromCloud(cloudRecord: ScheduleRead): ConflictSnapshot {
  return {
    title: cloudRecord.title,
    start_time: cloudRecord.start_time,
    end_time: cloudRecord.end_time,
    location: cloudRecord.location,
    remark: cloudRecord.remark,
    source: cloudRecord.source,
    updated_at: cloudRecord.updated_at,
    allow_rag_indexing: cloudRecord.allow_rag_indexing
  };
}

export function buildNewLocalScheduleRecord(draft: LocalScheduleDraft): LocalScheduleRecord {
  const storageStrategy = draft.storage_strategy ?? "local_only";
  return {
    local_id: createLocalId(),
    cloud_schedule_id: null,
    cloud_user_id: null,
    title: draft.title,
    start_time: draft.start_time,
    end_time: draft.end_time,
    location: draft.location ?? null,
    remark: draft.remark ?? null,
    source: draft.source ?? "manual",
    updated_at: nowIso(),
    cloud_updated_at: null,
    allow_rag_indexing: storageStrategy === "sync_to_cloud_and_knowledge",
    is_deleted: false,
    presence: "local_only",
    sync_intent: getInitialSyncIntent(storageStrategy),
    storage_strategy: storageStrategy,
    remove_local_after_push: false,
    conflict_reason: null,
    conflict_snapshot: null
  };
}

export function buildPulledCloudRecord(cloudRecord: ScheduleRead, cloudUserId: number): LocalScheduleRecord {
  return {
    local_id: createLocalId(),
    cloud_schedule_id: cloudRecord.id,
    cloud_user_id: cloudUserId,
    title: cloudRecord.title,
    start_time: cloudRecord.start_time,
    end_time: cloudRecord.end_time,
    location: cloudRecord.location,
    remark: cloudRecord.remark,
    source: cloudRecord.source,
    updated_at: cloudRecord.updated_at,
    cloud_updated_at: cloudRecord.updated_at,
    allow_rag_indexing: cloudRecord.allow_rag_indexing,
    is_deleted: false,
    presence: "local_and_cloud",
    sync_intent: "synced",
    storage_strategy: cloudRecord.allow_rag_indexing ? "sync_to_cloud_and_knowledge" : "sync_to_cloud",
    remove_local_after_push: false,
    conflict_reason: null,
    conflict_snapshot: null
  };
}

export function sortLocalScheduleRecords(records: LocalScheduleRecord[]): LocalScheduleRecord[] {
  return [...records].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}
