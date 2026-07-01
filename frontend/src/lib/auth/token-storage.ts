import { STORAGE_KEYS } from "@/lib/constants";

/**
 * Token storage backed by cookies.
 *
 * Cookies (not localStorage) are used so Next.js middleware can read the access
 * token server-side for route protection. They are NOT httpOnly — the backend
 * returns tokens in the JSON body, so the client owns them. Good enough for this
 * foundation; a later phase can move refresh tokens to an httpOnly cookie.
 */

const COOKIE_OPTS = "path=/; SameSite=Lax";
// Refresh-token lifetime mirrors the backend (7 days).
const MAX_AGE = 60 * 60 * 24 * 7;

function setCookie(name: string, value: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${MAX_AGE}; ${COOKIE_OPTS}`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; ${COOKIE_OPTS}`;
}

export const tokenStorage = {
  getAccess: () => getCookie(STORAGE_KEYS.accessToken),
  getRefresh: () => getCookie(STORAGE_KEYS.refreshToken),
  set: (access: string, refresh?: string) => {
    setCookie(STORAGE_KEYS.accessToken, access);
    if (refresh) setCookie(STORAGE_KEYS.refreshToken, refresh);
  },
  clear: () => {
    deleteCookie(STORAGE_KEYS.accessToken);
    deleteCookie(STORAGE_KEYS.refreshToken);
  },
};
