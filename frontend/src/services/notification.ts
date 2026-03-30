export type ReminderRequest = {
  id: number;
  title: string;
  body: string;
  at: Date;
};

export type ReminderResult = {
  mode: "capacitor" | "web-fallback";
  ok: boolean;
};

export async function scheduleReminder(request: ReminderRequest): Promise<ReminderResult> {
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.requestPermissions();
    await LocalNotifications.schedule({
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
    // Web fallback only logs intent; no persistent system notification scheduling.
    console.info(
      `[notification-fallback] id=${request.id} title=${request.title} at=${request.at.toISOString()}`
    );
    return { mode: "web-fallback", ok: false };
  }
}

