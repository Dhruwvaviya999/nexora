import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Activity } from "@/types/activity";

export type ActivityParams = {
  workspace?: string;
  action?: string;
  actor?: string;
  date_from?: string;
  date_to?: string;
  target_type?: string;
  target_id?: string;
  page?: number;
};

export const activitiesApi = {
  list: (params?: ActivityParams) =>
    apiClient.get<Paginated<Activity>>(API_ROUTES.activities, { params }),
};
