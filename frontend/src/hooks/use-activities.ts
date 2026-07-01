"use client";

import { useQuery } from "@tanstack/react-query";

import { activitiesApi } from "@/lib/api/activities";

interface ActivityParams {
  workspace?: string;
  action?: string;
  target_type?: string;
  target_id?: string;
}

export function useActivities(params: ActivityParams) {
  return useQuery({
    queryKey: ["activities", params],
    queryFn: () => activitiesApi.list(params),
    enabled: !!params.workspace || !!params.target_id,
  });
}
