import { env } from "@/config/env";

/** App-wide static metadata. */
export const APP = {
  name: "AI Knowledge & Workflow Assistant",
  shortName: "Nexora",
  description:
    "Your team's knowledge base and workflow automation, powered by AI.",
} as const;

/** Base URL of the versioned backend API (e.g. http://localhost:8000/api/v1). */
export const API_BASE_URL = env.NEXT_PUBLIC_API_URL;

/**
 * Centralised API route builders. Keep every endpoint path here so callers
 * never hard-code strings and future renames happen in one place.
 */
export const API_ROUTES = {
  health: "/health/",
} as const;

/** localStorage / cookie keys (auth tokens land here in Phase 2). */
export const STORAGE_KEYS = {
  accessToken: "nexora.accessToken",
  refreshToken: "nexora.refreshToken",
  theme: "nexora.theme",
} as const;
