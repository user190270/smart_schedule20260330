import { api, clearAccessToken, setAccessToken } from "@/api/client";

export type UserProfile = {
  id: number;
  username: string;
  role: "user" | "admin";
  is_active: boolean;
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

export async function logout(): Promise<void> {
  await clearAccessToken();
}
