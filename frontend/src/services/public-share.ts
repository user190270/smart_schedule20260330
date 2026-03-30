const PUBLIC_SHARE_PATH_PREFIX = "/share/public";

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function resolvePublicAppBaseUrl(): string {
  const envBase = import.meta.env.VITE_PUBLIC_APP_BASE_URL;
  if (typeof envBase === "string" && envBase.trim()) {
    return trimTrailingSlash(envBase.trim());
  }
  if (typeof window !== "undefined" && window.location?.origin) {
    return trimTrailingSlash(window.location.origin);
  }
  return "";
}

export function buildPublicSharePath(shareUuid: string): string {
  return `${PUBLIC_SHARE_PATH_PREFIX}/${shareUuid}`;
}

export function buildPublicShareLink(shareUuid: string): string {
  const baseUrl = resolvePublicAppBaseUrl();
  const path = buildPublicSharePath(shareUuid);
  return baseUrl ? `${baseUrl}${path}` : path;
}
