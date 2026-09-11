"use client";

import * as React from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/layout/page-container";
import { ROUTES } from "@/lib/constants";

/**
 * Error boundary for the authenticated app.
 *
 * Scoped to the `(app)` route group so a page-level crash keeps the sidebar
 * and header intact — the user stays oriented and can navigate away, rather
 * than being dropped onto a full-screen error.
 */
export default function AppSectionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Unhandled error in the app shell:", error);
  }, [error]);

  return (
    <PageContainer size="md" className="py-16">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="grid size-12 place-items-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="size-6" />
        </div>
        <div className="space-y-1">
          <h1 className="text-lg font-medium">This page hit an error</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            The rest of the app is still working. Try again, or head back to
            your dashboard.
          </p>
          {error.digest && (
            <p className="text-xs text-muted-foreground">
              Reference: <code className="font-mono">{error.digest}</code>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button onClick={reset}>Try again</Button>
          <Button variant="outline" asChild>
            <Link href={ROUTES.dashboard}>Back to dashboard</Link>
          </Button>
        </div>
      </div>
    </PageContainer>
  );
}
