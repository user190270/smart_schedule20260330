export function formatScheduleDateTime(isoText: string | null | undefined): string {
  if (!isoText) {
    return "未设置时间";
  }

  const dt = new Date(isoText);
  if (Number.isNaN(dt.getTime())) {
    return isoText;
  }

  return dt.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
}

export function formatScheduleRange(
  startTime: string | null | undefined,
  endTime: string | null | undefined
): string {
  if (!startTime) {
    return "未设置开始时间";
  }
  if (!endTime) {
    return `${formatScheduleDateTime(startTime)} · 未设置结束时间`;
  }
  return `${formatScheduleDateTime(startTime)} - ${formatScheduleDateTime(endTime)}`;
}

export function toDatetimeLocalValue(isoText: string | null | undefined): string {
  if (!isoText) {
    return "";
  }

  const dt = new Date(isoText);
  if (Number.isNaN(dt.getTime())) {
    return "";
  }

  const year = dt.getFullYear();
  const month = `${dt.getMonth() + 1}`.padStart(2, "0");
  const day = `${dt.getDate()}`.padStart(2, "0");
  const hour = `${dt.getHours()}`.padStart(2, "0");
  const minute = `${dt.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

export function fromDatetimeLocalValue(inputValue: string | null | undefined): string | null {
  if (!inputValue || !inputValue.trim()) {
    return null;
  }

  const dt = new Date(inputValue);
  if (Number.isNaN(dt.getTime())) {
    return null;
  }
  return dt.toISOString();
}

export function toOffsetIsoString(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  const hour = `${value.getHours()}`.padStart(2, "0");
  const minute = `${value.getMinutes()}`.padStart(2, "0");
  const second = `${value.getSeconds()}`.padStart(2, "0");
  const offsetMinutes = -value.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absoluteOffset = Math.abs(offsetMinutes);
  const offsetHour = `${Math.floor(absoluteOffset / 60)}`.padStart(2, "0");
  const offsetMinute = `${absoluteOffset % 60}`.padStart(2, "0");

  return `${year}-${month}-${day}T${hour}:${minute}:${second}${sign}${offsetHour}:${offsetMinute}`;
}
