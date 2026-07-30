"use client";

import { useQuery } from "@tanstack/react-query";

import { analyticsApi } from "@/lib/api/analytics";

export function useAnalytics(workspace?: string) {
  return useQuery({
    queryKey: ["analytics", workspace],
    queryFn: () => analyticsApi.get(workspace as string),
    enabled: !!workspace,
  });
}
