"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ROUTES } from "@/lib/constants";
import { useAuth } from "@/providers/auth-provider";

/**
 * Landing-page call to action.
 *
 * A live session goes straight to the dashboard; everyone else gets the
 * sign-up/sign-in pair. `useAuth` already draws that line for us: bootstrap
 * only sets a user once `/auth/me` succeeds (after the API client's silent
 * refresh) and clears the tokens when it doesn't, so a stale or expired session
 * shows the signed-out buttons rather than a dashboard link that would bounce
 * straight back to /login.
 */
export function HomeCta() {
  const { isAuthenticated, isLoading } = useAuth();

  // The session check runs client-side, so hold the row's height until it
  // resolves instead of flashing the wrong buttons.
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-3 pt-2">
        <Skeleton className="h-9 w-36 rounded-md" />
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center justify-center gap-3 pt-2">
        <Button asChild>
          <Link href={ROUTES.dashboard}>Go to dashboard</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-3 pt-2">
      <Button asChild>
        <Link href={ROUTES.register}>Get started</Link>
      </Button>
      <Button variant="outline" asChild>
        <Link href={ROUTES.login}>Sign in</Link>
      </Button>
    </div>
  );
}
