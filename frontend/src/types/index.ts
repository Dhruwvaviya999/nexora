/**
 * Shared application types. Domain models (User, Workspace, Project, …) are
 * added here in later phases as the API surface grows.
 */

/** Standard DRF paginated list response (PageNumberPagination). */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Normalised error shape thrown by the API client. */
export interface ApiError {
  status: number;
  message: string;
  /** Field-level validation errors keyed by field name, when present. */
  details?: Record<string, string[]>;
}

/** Response of GET /api/v1/health/. */
export interface HealthStatus {
  status: "ok" | "degraded";
  service: string;
  version: string;
  database: "ok" | "unavailable";
}
