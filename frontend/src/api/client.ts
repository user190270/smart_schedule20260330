import axios, { AxiosError, type AxiosAdapter, type AxiosRequestConfig, type AxiosResponse } from "axios";
import { CapacitorHttp } from "@capacitor/core";

import { getApiBaseUrl } from "@/services/runtime-config";
import { isNativeRuntime } from "@/services/runtime-config";
import { getStringValue, removeValue, setStringValue } from "@/services/local-store";

const ACCESS_TOKEN_KEY = "auth:access_token";

let accessTokenCache: string | null = null;
let tokenLoaded = false;

function buildRequestUrl(config: AxiosRequestConfig): string {
  const url = config.url ?? "";
  if (/^[a-z][a-z\d+\-.]*:\/\//i.test(url)) {
    return url;
  }

  const baseUrl = config.baseURL ?? getApiBaseUrl();
  return `${baseUrl.replace(/\/+$/, "")}/${url.replace(/^\/+/, "")}`;
}

function normalizeHeaders(headers: AxiosRequestConfig["headers"]): Record<string, string> {
  if (!headers) {
    return {};
  }

  const maybeJson = headers as { toJSON?: () => Record<string, unknown> };
  const raw = typeof maybeJson.toJSON === "function" ? maybeJson.toJSON() : (headers as Record<string, unknown>);

  return Object.fromEntries(
    Object.entries(raw)
      .filter(([, value]) => value !== undefined && value !== null)
      .map(([key, value]) => [key, String(value)])
  );
}

function normalizeParams(params: AxiosRequestConfig["params"]): Record<string, string> | undefined {
  if (!params) {
    return undefined;
  }

  if (params instanceof URLSearchParams) {
    return Object.fromEntries(params.entries());
  }

  return Object.fromEntries(
    Object.entries(params as Record<string, unknown>)
      .filter(([, value]) => value !== undefined && value !== null)
      .map(([key, value]) => [key, String(value)])
  );
}

function normalizeBody(data: AxiosRequestConfig["data"]): unknown {
  if (typeof data !== "string") {
    return data;
  }

  try {
    return JSON.parse(data);
  } catch {
    return data;
  }
}

function normalizeResponseData(data: unknown): unknown {
  if (typeof data !== "string") {
    return data;
  }

  const trimmed = data.trim();
  if (!trimmed) {
    return data;
  }

  const looksLikeJson =
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"));

  if (!looksLikeJson) {
    return data;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return data;
  }
}

const nativeHttpAdapter: AxiosAdapter = async (config) => {
  try {
    const response = await CapacitorHttp.request({
      url: buildRequestUrl(config),
      method: (config.method ?? "GET").toUpperCase(),
      headers: normalizeHeaders(config.headers),
      params: normalizeParams(config.params),
      data: normalizeBody(config.data),
      connectTimeout: config.timeout,
      readTimeout: config.timeout,
      responseType: config.responseType === "text" ? "text" : "json"
    });

    const axiosResponse = {
      data: normalizeResponseData(response.data),
      status: response.status,
      statusText: `${response.status}`,
      headers: response.headers ?? {},
      config,
      request: null
    } satisfies AxiosResponse;

    const validateStatus = config.validateStatus ?? ((status: number) => status >= 200 && status < 300);
    if (!validateStatus(axiosResponse.status)) {
      throw new AxiosError(
        `Request failed with status code ${axiosResponse.status}`,
        undefined,
        config,
        null,
        axiosResponse
      );
    }

    return axiosResponse;
  } catch (error) {
    if (error instanceof AxiosError) {
      throw error;
    }
    if (error instanceof Error) {
      throw new AxiosError(error.message, "ERR_NETWORK", config);
    }
    throw error;
  }
};

async function ensureTokenLoaded() {
  if (tokenLoaded) {
    return;
  }
  accessTokenCache = await getStringValue(ACCESS_TOKEN_KEY);
  tokenLoaded = true;
}

export async function setAccessToken(token: string): Promise<void> {
  accessTokenCache = token;
  tokenLoaded = true;
  await setStringValue(ACCESS_TOKEN_KEY, token);
}

export async function clearAccessToken(): Promise<void> {
  accessTokenCache = null;
  tokenLoaded = true;
  await removeValue(ACCESS_TOKEN_KEY);
}

export function getAccessTokenSync(): string | null {
  return accessTokenCache;
}

export async function getAccessToken(): Promise<string | null> {
  await ensureTokenLoaded();
  return accessTokenCache;
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000
});

if (isNativeRuntime()) {
  api.defaults.adapter = nativeHttpAdapter;
}

api.interceptors.request.use(async (config) => {
  await ensureTokenLoaded();
  if (accessTokenCache) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${accessTokenCache}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const statusCode = error?.response?.status;
    if (statusCode === 401 && accessTokenCache) {
      await clearAccessToken();
    }
    return Promise.reject(error);
  }
);

export type HealthResponse = {
  status: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}
