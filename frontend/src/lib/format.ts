/** Small formatting helpers shared across tables and detail pages. */

export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/** Matches a bare calendar date with no time or zone, e.g. `2026-09-14`. */
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Parse a date value into a `Date`. Bare `YYYY-MM-DD` strings are read as local
 * midnight; `new Date("2026-09-14")` would read them as UTC and land on the
 * neighbouring day for anyone not on UTC.
 */
export function parseDate(value?: string | null): Date | undefined {
  if (!value) return undefined;
  if (DATE_ONLY.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed;
}

/** Serialize a `Date` to `YYYY-MM-DD` using its local calendar day. */
export function toDateOnly(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDate(value?: string | null): string {
  const date = parseDate(value);
  if (!date) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(value?: string | null): string {
  const date = parseDate(value);
  if (!date) return "—";
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Compact relative time like "just now", "5m", "3h", "2d", else a date. */
export function formatRelativeTime(value?: string | null): string {
  const date = parseDate(value);
  if (!date) return "—";
  const then = date.getTime();
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d`;
  return formatDate(value);
}

/** True when a date string is strictly before today (used for overdue tasks). */
export function isPast(value?: string | null): boolean {
  const date = parseDate(value);
  if (!date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date < today;
}
