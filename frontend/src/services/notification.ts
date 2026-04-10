import { Capacitor } from "@capacitor/core";

export type ReminderRequest = {
  id: number;
  title: string;
  body: string;
  at: Date;
};

export type ReminderResult = {
  mode: "capacitor" | "web-fallback";
  ok: boolean;
  reason?: "permission_denied" | "plugin_unavailable";
};

export type ScheduleReminderTarget = {
  localId: string;
  title: string;
  startTime: string | null | undefined;
  location?: string | null;
  isDeleted?: boolean;
};

export type ScheduleReminderSyncResult = ReminderResult & {
  action: "scheduled" | "cancelled" | "skipped";
  notificationId: number;
  skipReason?: "deleted" | "invalid_start_time" | "past_start_time";
};

async function loadLocalNotifications() {
  if (!Capacitor.isNativePlatform()) {
    return null;
  }

  try {
    const module = await import("@capacitor/local-notifications");
    // Return a plain object so async resolution does not probe plugin.then().
    return { localNotifications: module.LocalNotifications };
  } catch {
    return null;
  }
}

function logNotificationFallback(action: "schedule" | "cancel", detail: string) {
  console.info(`[notification-fallback] action=${action} ${detail}`);
}

function buildScheduleReminderBody(target: ScheduleReminderTarget): string {
  const location = target.location?.trim();
  if (location) {
    return `日程即将开始 · ${location}`;
  }
  return "日程即将开始";
}

function parseReminderDate(startTime: string | null | undefined): Date | null {
  if (!startTime) {
    return null;
  }

  const at = new Date(startTime);
  if (Number.isNaN(at.getTime())) {
    return null;
  }
  return at;
}

export function getScheduleReminderId(localId: string): number {
  let hash = 2166136261;

  for (let index = 0; index < localId.length; index += 1) {
    hash ^= localId.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  const normalized = (hash >>> 1) % 2147483647;
  return normalized === 0 ? 1 : normalized;
}

export async function scheduleReminder(request: ReminderRequest): Promise<ReminderResult> {
  const loadedNotifications = await loadLocalNotifications();
  if (!loadedNotifications) {
    logNotificationFallback(
      "schedule",
      `id=${request.id} title=${request.title} at=${request.at.toISOString()}`
    );
    return { mode: "web-fallback", ok: false, reason: "plugin_unavailable" };
  }

  const notifications = loadedNotifications.localNotifications;

  try {
    const permission = await notifications.requestPermissions();
    if (permission.display !== "granted") {
      return { mode: "capacitor", ok: false, reason: "permission_denied" };
    }

    await notifications.schedule({
      notifications: [
        {
          id: request.id,
          title: request.title,
          body: request.body,
          schedule: { at: request.at }
        }
      ]
    });
    return { mode: "capacitor", ok: true };
  } catch {
    logNotificationFallback(
      "schedule",
      `id=${request.id} title=${request.title} at=${request.at.toISOString()}`
    );
    return { mode: "web-fallback", ok: false, reason: "plugin_unavailable" };
  }
}

export async function cancelReminder(id: number): Promise<ReminderResult> {
  const loadedNotifications = await loadLocalNotifications();
  if (!loadedNotifications) {
    logNotificationFallback("cancel", `id=${id}`);
    return { mode: "web-fallback", ok: false, reason: "plugin_unavailable" };
  }

  const notifications = loadedNotifications.localNotifications;

  try {
    await notifications.cancel({
      notifications: [{ id }]
    });
    return { mode: "capacitor", ok: true };
  } catch {
    logNotificationFallback("cancel", `id=${id}`);
    return { mode: "web-fallback", ok: false, reason: "plugin_unavailable" };
  }
}

export async function syncScheduleReminder(target: ScheduleReminderTarget): Promise<ScheduleReminderSyncResult> {
  const notificationId = getScheduleReminderId(target.localId);

  if (target.isDeleted) {
    const result = await cancelReminder(notificationId);
    return {
      ...result,
      action: "cancelled",
      notificationId,
      skipReason: "deleted"
    };
  }

  const at = parseReminderDate(target.startTime);
  if (!at) {
    const result = await cancelReminder(notificationId);
    return {
      ...result,
      action: "skipped",
      notificationId,
      skipReason: "invalid_start_time"
    };
  }

  if (at.getTime() <= Date.now()) {
    const result = await cancelReminder(notificationId);
    return {
      ...result,
      action: "skipped",
      notificationId,
      skipReason: "past_start_time"
    };
  }

  await cancelReminder(notificationId);
  const result = await scheduleReminder({
    id: notificationId,
    title: target.title,
    body: buildScheduleReminderBody(target),
    at
  });

  return {
    ...result,
    action: "scheduled",
    notificationId
  };
}

export async function cancelScheduleReminder(localId: string): Promise<ScheduleReminderSyncResult> {
  const notificationId = getScheduleReminderId(localId);
  const result = await cancelReminder(notificationId);

  return {
    ...result,
    action: "cancelled",
    notificationId
  };
}

