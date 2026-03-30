import { api } from "@/api/client";
import type { ScheduleRead, ScheduleSource } from "@/api/schedules";

export type SyncScheduleRecord = {
  id?: number | null;
  title: string;
  start_time: string;
  end_time: string | null;
  location?: string | null;
  remark?: string | null;
  source: ScheduleSource;
  updated_at: string;
  allow_rag_indexing: boolean;
  is_deleted: boolean;
};

export type SyncPushResultItem = {
  schedule_id: number;
  status: "created" | "updated" | "ignored";
  reason: string | null;
};

export type SyncPushResponse = {
  results: SyncPushResultItem[];
};

export type SyncPullResponse = {
  records: ScheduleRead[];
};

export type SyncStatusResponse = {
  cloud_schedule_count: number;
  knowledge_base_eligible_schedule_count: number;
  indexed_schedule_count: number;
  indexed_chunk_count: number;
  last_knowledge_rebuild_at: string | null;
  last_knowledge_rebuild_status: "idle" | "success" | "failed";
  last_knowledge_rebuild_message: string | null;
  last_knowledge_rebuild_schedules_considered: number;
  last_knowledge_rebuild_schedules_indexed: number;
  last_knowledge_rebuild_chunks_created: number;
  embedding_dimensions: number;
  cloud_connection_status: "connected";
};

export async function pushSchedules(records: SyncScheduleRecord[]): Promise<SyncPushResponse> {
  const response = await api.post<SyncPushResponse>("/sync/push", { records });
  return response.data;
}

export async function pullSchedules(): Promise<SyncPullResponse> {
  const response = await api.get<SyncPullResponse>("/sync/pull");
  return response.data;
}

export async function fetchSyncStatus(): Promise<SyncStatusResponse> {
  const response = await api.get<SyncStatusResponse>("/sync/status");
  return response.data;
}
