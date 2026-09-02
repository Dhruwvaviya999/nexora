import { describe, expect, it } from "vitest";

import { formatDate, isPast, parseDate, toDateOnly } from "./format";

describe("parseDate", () => {
  it("reads a bare YYYY-MM-DD as local midnight", () => {
    const date = parseDate("2026-09-14")!;
    expect(date.getFullYear()).toBe(2026);
    expect(date.getMonth()).toBe(8);
    expect(date.getDate()).toBe(14);
    expect(date.getHours()).toBe(0);
  });

  it("still parses full timestamps", () => {
    expect(parseDate("2026-09-14T10:30:00Z")?.toISOString()).toBe(
      "2026-09-14T10:30:00.000Z"
    );
  });

  it("returns undefined for empty or invalid values", () => {
    expect(parseDate(null)).toBeUndefined();
    expect(parseDate("")).toBeUndefined();
    expect(parseDate("not-a-date")).toBeUndefined();
  });
});

describe("toDateOnly", () => {
  it("uses the local calendar day, not UTC", () => {
    expect(toDateOnly(new Date(2026, 8, 14))).toBe("2026-09-14");
    expect(toDateOnly(new Date(2026, 0, 1))).toBe("2026-01-01");
  });

  it("round-trips every day of a month in the local timezone", () => {
    for (let day = 1; day <= 30; day += 1) {
      const value = `2026-09-${String(day).padStart(2, "0")}`;
      expect(toDateOnly(parseDate(value)!)).toBe(value);
    }
  });
});

describe("formatDate", () => {
  it("shows the picked day rather than its UTC neighbour", () => {
    expect(formatDate("2026-09-14")).toContain("14");
    expect(formatDate("2026-09-28")).toContain("28");
  });

  it("falls back to an em dash when empty", () => {
    expect(formatDate(null)).toBe("—");
  });
});

describe("isPast", () => {
  it("treats today as not past", () => {
    expect(isPast(toDateOnly(new Date()))).toBe(false);
  });

  it("flags yesterday", () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(isPast(toDateOnly(yesterday))).toBe(true);
  });
});
