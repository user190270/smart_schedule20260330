import { api } from "@/api/client";

export type AdminUserView = {
  id: number;
  username: string;
  role: "user" | "admin";
  is_active: boolean;
  daily_token_usage: number;
  last_reset_time: string;
};

export type AdminUserUpdatePayload = {
  is_active?: boolean;
  reset_quota?: boolean;
};

export async function listAdminUsers(): Promise<AdminUserView[]> {
  const response = await api.get<AdminUserView[]>("/admin/users");
  return response.data;
}

export async function updateAdminUser(userId: number, payload: AdminUserUpdatePayload): Promise<AdminUserView> {
  const response = await api.patch<AdminUserView>(`/admin/users/${userId}`, payload);
  return response.data;
}
