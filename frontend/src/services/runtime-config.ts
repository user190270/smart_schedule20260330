import { Capacitor } from "@capacitor/core";

const DEFAULT_WEB_API_BASE_URL = "http://localhost:8000/api";
const DEFAULT_LAN_API_BASE_URL = "http://192.168.1.100:8000/api";

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

function getConfiguredApiBaseUrl(): string | null {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (typeof configured !== "string") {
    return null;
  }
  const normalized = normalizeUrl(configured);
  return normalized.length > 0 ? normalized : null;
}

export function isNativeRuntime(): boolean {
  return Capacitor.isNativePlatform();
}

export function getDefaultApiBaseUrl(): string {
  return isNativeRuntime() ? DEFAULT_LAN_API_BASE_URL : DEFAULT_WEB_API_BASE_URL;
}

export function getApiBaseUrl(): string {
  return getConfiguredApiBaseUrl() ?? getDefaultApiBaseUrl();
}
