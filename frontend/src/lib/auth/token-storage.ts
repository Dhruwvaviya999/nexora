import { STORAGE_KEYS } from "@/lib/constants";

/**
 * Token storage.
 *
 * Two values, deliberately stored very differently:
 *
 * 1. **Refresh token — never touched by this module.** It lives in an
 *    `httpOnly` cookie set by the backend on the API's origin. Page script
 *    cannot read it, so an XSS cannot exfiltrate a week-long session. It is
 *    attached automatically by `credentials: "include"` on the two auth
 *    endpoints that need it.
 *
 * 2. **Access token — in memory only.** A module-scoped variable, so it dies
 *    with the tab and is never written anywhere a script or an extension can
 *    scrape it at rest. It expires in 15 minutes regardless, and a page reload
 *    silently re-obtains one from the refresh cookie.
 *
 * The third value is the `nexora.session` flag: a cookie on the *frontend*
 * origin containing the literal string "1" and no secret whatsoever. It exists
 * only so `src/proxy.ts` — which runs at the edge on port 3000 and therefore
 * cannot see a cookie scoped to the API on port 8000 — can decide whether to
 * render a page or redirect to /login. Forging it gains an attacker nothing:
 * the page loads, the API rejects every request, and the app bounces them
 * straight back out.
 */

/** Non-secret marker cookie, readable by the edge guard. */
const SESSION_FLAG_MAX_AGE = 60 * 60 * 24 * 7; // mirrors the refresh lifetime
const SESSION_FLAG_OPTS = "path=/; SameSite=Lax";

/** The access token. Module scope: memory only, never persisted. */
let accessToken: string | null = null;

/** Notifies subscribers (the websocket hook) when the token changes. */
const listeners = new Set<(token: string | null) => void>();

function isSecureContext(): boolean {
  return typeof window !== "undefined" && window.location.protocol === "https:";
}

function setSessionFlag(active: boolean) {
  if (typeof document === "undefined") return;
  // `Secure` whenever the page is served over HTTPS, so the marker is not
  // leaked over a plaintext downgrade.
  const secure = isSecureContext() ? "; Secure" : "";
  try {
    document.cookie = active
      ? `${STORAGE_KEYS.sessionFlag}=1; Max-Age=${SESSION_FLAG_MAX_AGE}; ${SESSION_FLAG_OPTS}${secure}`
      : `${STORAGE_KEYS.sessionFlag}=; Max-Age=0; ${SESSION_FLAG_OPTS}${secure}`;
  } catch {
    // Private browsing or blocked site data. The marker is only a hint for the
    // edge guard: losing it costs one redirect, never correctness, so this
    // must not take down login.
  }
}

export const tokenStorage = {
  /** Current in-memory access token, or null. */
  getAccess: (): string | null => accessToken,

  /** Store a freshly issued access token and mark the session as live. */
  setAccess: (token: string) => {
    accessToken = token;
    setSessionFlag(true);
    listeners.forEach((fn) => fn(token));
  },

  /**
   * Forget everything this client holds.
   *
   * Only clears the *local* side: the httpOnly refresh cookie can only be
   * removed by the server, which `POST /auth/logout/` does.
   */
  clear: () => {
    accessToken = null;
    setSessionFlag(false);
    listeners.forEach((fn) => fn(null));
  },

  /** True when the edge guard's marker cookie is present. */
  hasSessionFlag: (): boolean => {
    if (typeof document === "undefined") return false;
    try {
      return document.cookie
        .split("; ")
        .some((row) => row.startsWith(`${STORAGE_KEYS.sessionFlag}=1`));
    } catch {
      return false;
    }
  },

  /** Subscribe to access-token changes. Returns an unsubscribe function. */
  subscribe: (fn: (token: string | null) => void) => {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
