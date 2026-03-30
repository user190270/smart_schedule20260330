import { api } from "@/api/client";

export type ShareScheduleDto = {
  title: string;
  start_time: string;
  end_time: string | null;
  location: string | null;
  remark: string | null;
  source: "manual" | "ai_parsed";
  updated_at: string;
  is_deleted: boolean;
};

export type ShareCreateResponse = {
  share_uuid: string;
  share_path: string;
  schedule: ShareScheduleDto;
};

export async function createShareLink(scheduleId: number): Promise<ShareCreateResponse> {
  const response = await api.post<ShareCreateResponse>(`/share/schedules/${scheduleId}`);
  return response.data;
}

export async function fetchSharedSchedule(shareUuid: string): Promise<ShareScheduleDto> {
  const response = await api.get<ShareScheduleDto>(`/share/${shareUuid}`);
  return response.data;
}
