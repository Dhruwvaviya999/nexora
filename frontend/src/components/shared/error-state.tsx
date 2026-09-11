"use client";

import * as React from "react";
import { AlertTriangle, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getErrorMessage, isApiError } from "@/lib/api/errors";

/**
 * Inline error placeholder for a failed query.
 *
 * Detail and list pages previously rendered `if (isLoading || !data)` as a
 * spinner, which meant a *failed* fetch was indistinguishable from a slow one
 * and spun forever. Branch on `isError` and render this instead.
 *
 * The message is derived from the normalised `ApiError`, so a 403 shows the
 * server's specific reason ("Only workspace owners… can review handovers")
 * rather than a generic failure.
 */
export function ErrorState({
  error,
  onRetry,
  title,
  className,
}: {
  error?: unknown;
  onRetry?: () => void;
  title?: string;
  className?: string;
}) {
  const status = isApiError(error) ? error.status : undefined;
  const heading = title ?? headingFor(status);

  return (
    <div
      role="alert"
      className={
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-16 text-center " +
        (className ?? "")
      }
    >
      <div className="grid size-11 place-items-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="size-5" />
      </div>
      <div className="space-y-1">
        <p className="font-medium">{heading}</p>
        <p className="mx-auto max-w-sm text-sm text-muted-foreground">
          {error ? getErrorMessage(error) : "Please try again."}
        </p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="size-4" />
          Try again
        </Button>
      )}
    </div>
  );
}

function headingFor(status?: number): string {
  switch (status) {
    case 403:
      return "You don't have access to this";
    case 404:
      return "Not found";
    case 429:
      return "Too many requests";
    case 502:
    case 503:
      return "Service unavailable";
    default:
      return "Something went wrong";
  }
}
