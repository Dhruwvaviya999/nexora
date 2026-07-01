"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { HealthStatus } from "@/types";

/**
 * Example data hook wiring the API client + TanStack Query together.
 * Polls the backend health endpoint; serves as the template every future
 * feature hook (workspaces, projects, …) will follow.
 */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<HealthStatus>(API_ROUTES.health),
    refetchInterval: 30_000,
  });
}
