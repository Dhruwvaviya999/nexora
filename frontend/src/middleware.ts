import { NextResponse, type NextRequest } from "next/server";

import { STORAGE_KEYS } from "@/lib/constants";

/**
 * Edge route guard.
 *
 * Reads the access-token cookie (set client-side after login) to gate routes.
 * It only checks *presence*, not validity — the API client handles expiry via
 * silent refresh, and the protected layout redirects if the session is truly
 * dead. This keeps middleware fast and avoids verifying JWTs at the edge.
 */

const PROTECTED_PREFIXES = ["/dashboard", "/workspaces"];
const AUTH_PAGES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasToken = Boolean(
    request.cookies.get(STORAGE_KEYS.accessToken)?.value ||
      request.cookies.get(STORAGE_KEYS.refreshToken)?.value
  );

  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

  if (isProtected && !hasToken) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && hasToken) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/workspaces/:path*", "/login", "/register"],
};
