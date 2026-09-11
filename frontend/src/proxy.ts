import { NextResponse, type NextRequest } from "next/server";

import { STORAGE_KEYS } from "@/lib/constants";

/**
 * Route guard, run at the edge for every matched request before it reaches a
 * route.
 *
 * It reads `nexora.session` — a marker cookie whose value is the literal
 * string "1". It is **not** a credential and contains no token. The real
 * refresh token is an httpOnly cookie scoped to the API's origin, which this
 * middleware (running on the frontend origin) cannot see and does not need.
 *
 * The check is presence-only and is purely a UX optimisation: it avoids
 * rendering an app shell for someone obviously signed out, and bounces a
 * signed-in visitor off the login page. Forging the cookie gains an attacker
 * nothing — the page renders, every API call 401s, and the protected layout
 * redirects straight back out. **Authorisation is enforced by the API, not
 * here.**
 */

// Every authenticated route tree. Previously only /dashboard and /workspaces
// were matched, so ten other protected trees rendered a shell and then
// redirected — a visible flash, and an inconsistent story about what is
// guarded.
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/workspaces",
  "/projects",
  "/tasks",
  "/handovers",
  "/documents",
  "/ai",
  "/activity",
  "/search",
  "/settings",
  "/notifications",
  "/invitations",
];

// Signing in makes these pages pointless, so a session bounces off them.
//
// The password-reset pages are deliberately absent: someone already signed in
// on this browser must still be able to open a reset link from their email and
// finish setting a new password. Bouncing them to the dashboard would leave
// them unable to complete a reset they legitimately asked for.
const AUTH_PAGES = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.get(STORAGE_KEYS.sessionFlag)?.value === "1";

  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

  if (isProtected && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/workspaces/:path*",
    "/projects/:path*",
    "/tasks/:path*",
    "/handovers/:path*",
    "/documents/:path*",
    "/ai/:path*",
    "/activity/:path*",
    "/search/:path*",
    "/settings/:path*",
    "/notifications/:path*",
    "/invitations/:path*",
    "/login",
    "/register",
  ],
};
