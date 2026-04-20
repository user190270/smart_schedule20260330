import { api, clearAccessToken, setAccessToken } from "@/api/client";

export type SubscriptionTier = "free" | "plus" | "pro";

export type UserProfile = {
  id: number;
  username: string;
  role: "user" | "admin";
  is_active: boolean;
  notification_email: string | null;
  subscription_tier: SubscriptionTier;
  daily_token_usage: number;
  daily_token_limit: number;
};

export type AuthTokenResponse = {
  user: UserProfile;
  access_token: string;
  token_type: "bearer";
  expires_in: number;
};

export type RegisterPayload = {
  username: string;
  password: string;
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type UpdateProfilePayload = {
  notification_email: string | null;
};

export async function register(payload: RegisterPayload): Promise<AuthTokenResponse> {
  const response = await api.post<AuthTokenResponse>("/auth/register", payload);
  await setAccessToken(response.data.access_token);
  return response.data;
}

export async function login(payload: LoginPayload): Promise<AuthTokenResponse> {
  const response = await api.post<AuthTokenResponse>("/auth/login", payload);
  await setAccessToken(response.data.access_token);
  return response.data;
}

export async function fetchMe(): Promise<UserProfile> {
  const response = await api.get<UserProfile>("/auth/me");
  return response.data;
}

export async function updateMe(payload: UpdateProfilePayload): Promise<UserProfile> {
  const response = await api.patch<UserProfile>("/auth/me", payload);
  return response.data;
}

export async function demoUpgradeMe(targetTier?: SubscriptionTier): Promise<UserProfile> {
  const response = await api.post<UserProfile>("/auth/me/demo-upgrade", targetTier ? { target_tier: targetTier } : {});
  return response.data;
}

export async function logout(): Promise<void> {
  await clearAccessToken();
}
