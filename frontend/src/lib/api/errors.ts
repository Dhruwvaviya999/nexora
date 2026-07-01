import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import type { ApiError } from "@/types";

/** Narrow an unknown thrown value to our ApiError shape. */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    "message" in error
  );
}

/** Human-readable top-level message for a toast. */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

/**
 * Map a DRF validation error (`{ field: ["msg"] }`) onto react-hook-form
 * fields so messages render inline next to the right input.
 */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>
): void {
  if (!isApiError(error) || !error.details) return;
  for (const [field, messages] of Object.entries(error.details)) {
    if (Array.isArray(messages) && messages.length) {
      setError(field as Path<T>, { type: "server", message: messages[0] });
    }
  }
}
