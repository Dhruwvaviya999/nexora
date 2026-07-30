"use client";

import { useQuery } from "@tanstack/react-query";

import { activitiesApi, type ActivityParams } from "@/lib/api/activities";

export function useActivities(params: ActivityParams) {
  return useQuery({
    queryKey: ["activities", params],
    queryFn: () => activitiesApi.list(params),
    enabled: !!params.workspace || !!params.target_id,
  });
}
