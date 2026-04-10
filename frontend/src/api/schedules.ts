import { api } from "@/api/client";

export type ScheduleSource = "manual" | "ai_parsed";

export type ScheduleRead = {
  id: number;
  user_id: number;
  title: string;
  start_time: string;
  end_time: string | null;
  location: string | null;
  remark: string | null;
  source: ScheduleSource;
  updated_at: string;
  allow_rag_indexing: boolean;
  email_reminder_enabled: boolean;
  email_remind_before_minutes: number | null;
  is_deleted: boolean;
};

export type ScheduleCreate = {
  title: string;
  start_time: string;
  end_time: string | null;
  location?: string | null;
  remark?: string | null;
  source?: ScheduleSource;
  confirmed_by_user?: boolean;
  allow_rag_indexing?: boolean;
  email_reminder_enabled?: boolean;
  email_remind_before_minutes?: number | null;
};

export type ScheduleUpdate = {
  title?: string;
  start_time?: string;
  end_time?: string | null;
  location?: string | null;
  remark?: string | null;
  source?: ScheduleSource;
  allow_rag_indexing?: boolean;
  email_reminder_enabled?: boolean;
  email_remind_before_minutes?: number | null;
  is_deleted?: boolean;
};

export async function listSchedules(includeDeleted = false): Promise<ScheduleRead[]> {
  const response = await api.get<ScheduleRead[]>("/schedules", {
    params: { include_deleted: includeDeleted }
  });
  return response.data;
}

export async function createSchedule(payload: ScheduleCreate): Promise<ScheduleRead> {
  const response = await api.post<ScheduleRead>("/schedules", payload);
  return response.data;
}

export async function updateSchedule(scheduleId: number, payload: ScheduleUpdate): Promise<ScheduleRead> {
  const response = await api.patch<ScheduleRead>(`/schedules/${scheduleId}`, payload);
  return response.data;
}

export async function deleteSchedule(scheduleId: number): Promise<void> {
  await api.delete(`/schedules/${scheduleId}`);
}
