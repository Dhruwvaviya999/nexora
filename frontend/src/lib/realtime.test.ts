import { describe, expect, it, vi } from "vitest";

const env = vi.hoisted(() => ({ NEXT_PUBLIC_API_URL: "http://localhost:8000/api/v1" }));
vi.mock("@/config/env", () => ({ env }));

import { notificationSocketUrl } from "./realtime";

describe("notificationSocketUrl", () => {
  it("points at the socket route on the API host, not under the REST prefix", () => {
    env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";

    const url = new URL(notificationSocketUrl("tok"));

    expect(url.host).toBe("localhost:8000");
    expect(url.pathname).toBe("/ws/notifications/");
  });

  it("upgrades https to wss so the socket is not the weak link", () => {
    env.NEXT_PUBLIC_API_URL = "https://api.example.com/api/v1";

    expect(notificationSocketUrl("tok").startsWith("wss://")).toBe(true);
  });

  it("uses ws for plain http", () => {
    env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";

    expect(notificationSocketUrl("tok").startsWith("ws://")).toBe(true);
  });

  it("escapes the token so it cannot inject extra query parameters", () => {
    env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api/v1";

    const url = new URL(notificationSocketUrl("a&b=c d"));

    expect(url.searchParams.get("token")).toBe("a&b=c d");
    expect(url.searchParams.get("b")).toBeNull();
  });
});
