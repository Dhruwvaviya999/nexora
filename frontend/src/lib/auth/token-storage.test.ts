import { beforeEach, describe, expect, it, vi } from "vitest";

import { tokenStorage } from "@/lib/auth/token-storage";
import { STORAGE_KEYS } from "@/lib/constants";

/**
 * The security contract of token storage.
 *
 * The refresh token is an httpOnly cookie set by the backend, so it must be
 * absent from anything this module touches. What is asserted here is the
 * negative space: no token is ever written to a place script can read at rest.
 */

function clearCookies() {
  document.cookie
    .split("; ")
    .filter(Boolean)
    .forEach((row) => {
      const name = row.split("=")[0];
      document.cookie = `${name}=; Max-Age=0; path=/`;
    });
}

describe("tokenStorage", () => {
  beforeEach(() => {
    clearCookies();
    tokenStorage.clear();
  });

  it("holds the access token in memory, not in a cookie", () => {
    tokenStorage.setAccess("access-token-value");

    expect(tokenStorage.getAccess()).toBe("access-token-value");
    // The token itself must never be written to document.cookie.
    expect(document.cookie).not.toContain("access-token-value");
  });

  it("never writes a refresh token anywhere", () => {
    tokenStorage.setAccess("access-token-value");

    expect(document.cookie).not.toMatch(/refresh/i);
    expect(Object.keys(STORAGE_KEYS)).not.toContain("refreshToken");
    expect(Object.keys(STORAGE_KEYS)).not.toContain("accessToken");
  });

  it("sets a value-less session marker the edge guard can read", () => {
    tokenStorage.setAccess("access-token-value");

    expect(tokenStorage.hasSessionFlag()).toBe(true);
    // The marker carries no secret — just "1".
    expect(document.cookie).toContain(`${STORAGE_KEYS.sessionFlag}=1`);
  });

  it("reports no session before login", () => {
    expect(tokenStorage.getAccess()).toBeNull();
    expect(tokenStorage.hasSessionFlag()).toBe(false);
  });

  it("clear() drops both the in-memory token and the marker", () => {
    tokenStorage.setAccess("access-token-value");
    tokenStorage.clear();

    expect(tokenStorage.getAccess()).toBeNull();
    expect(tokenStorage.hasSessionFlag()).toBe(false);
  });

  it("notifies subscribers when the token changes", () => {
    const seen: (string | null)[] = [];
    const unsubscribe = tokenStorage.subscribe((t) => seen.push(t));

    tokenStorage.setAccess("first");
    tokenStorage.clear();
    unsubscribe();
    tokenStorage.setAccess("after-unsubscribe");

    expect(seen).toEqual(["first", null]);
  });

  it("survives blocked cookie storage without breaking login", () => {
    // Private-browsing modes can make document.cookie throw on write. The
    // marker is only a hint for the edge guard, so losing it must cost one
    // redirect — never the session itself.
    const spy = vi.spyOn(document, "cookie", "set").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(() => tokenStorage.setAccess("token")).not.toThrow();
    // The access token is in memory, so it is unaffected.
    expect(tokenStorage.getAccess()).toBe("token");

    spy.mockRestore();
  });
});
