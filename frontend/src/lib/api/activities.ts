import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Activity } from "@/types/activity";

type ActivityParams = {
  workspace?: string;
  action?: string;
  target_type?: string;
  target_id?: string;
};

export const activitiesApi = {
  list: (params?: ActivityParams) =>
    apiClient.get<Paginated<Activity>>(API_ROUTES.activities, { params }),
};
