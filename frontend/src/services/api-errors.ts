type QuotaErrorDetail = {
  error_code?: string;
  message?: string;
  subscription_tier?: "free" | "plus" | "pro";
  daily_token_usage?: number;
  daily_token_limit?: number;
};

const tierLabels: Record<NonNullable<QuotaErrorDetail["subscription_tier"]>, string> = {
  free: "免费层级",
  plus: "Plus 演示层级",
  pro: "Pro 演示层级"
};

function isQuotaErrorDetail(detail: unknown): detail is QuotaErrorDetail {
  return Boolean(
      detail &&
      typeof detail === "object" &&
      "error_code" in detail &&
      (detail as { error_code?: string }).error_code === "daily_token_quota_exceeded"
  );
}

function formatQuotaErrorDetail(detail: QuotaErrorDetail): string {
  const tier = detail.subscription_tier ? tierLabels[detail.subscription_tier] : "当前层级";
  const usage = typeof detail.daily_token_usage === "number" ? detail.daily_token_usage : "?";
  const limit = typeof detail.daily_token_limit === "number" ? detail.daily_token_limit : "?";
  return `已达到${tier}今日 token 上限（${usage}/${limit}）。请点击头像进入配额管理后再试。`;
}

export function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (isQuotaErrorDetail(detail)) {
    return formatQuotaErrorDetail(detail);
  }
  if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") {
    return detail.message;
  }
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  return fallback;
}

export function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "response" in error) {
    const maybeResponse = error as { response?: { data?: { detail?: unknown } } };
    return formatApiErrorDetail(maybeResponse.response?.data?.detail, fallback);
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

export async function buildFetchError(response: Response, fallback: string): Promise<Error> {
  const rawText = await response.text();
  if (rawText.trim()) {
    try {
      const parsed = JSON.parse(rawText) as { detail?: unknown };
      return new Error(formatApiErrorDetail(parsed.detail ?? parsed, fallback));
    } catch {
      return new Error(rawText);
    }
  }
  return new Error(fallback);
}
