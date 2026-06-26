"use client";

import { useQuery } from "@tanstack/react-query";

import { dashboardApi } from "@/lib/api/dashboard";

export function useDashboard(workspace: string | undefined) {
  return useQuery({
    queryKey: ["dashboard", workspace],
    queryFn: () => dashboardApi.get(workspace as string),
    enabled: !!workspace,
  });
}
