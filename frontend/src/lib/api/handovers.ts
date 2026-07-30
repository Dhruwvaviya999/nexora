import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Handover, HandoverStatus } from "@/types/handover";

export type HandoverListParams = {
  workspace?: string;
  task?: string;
  project?: string;
  status?: string;
  from_user?: string;
  to_user?: string;
  search?: string;
  ordering?: string;
  page?: number;
};

/** Payload accepted by create/update (relations sent as ids). */
export interface HandoverPayload {
  task?: string;
  to_user_id?: string;
  summary?: string;
  pending_items?: string;
  resources?: string;
}

export interface HandoverReviewPayload {
  decision: Exclude<HandoverStatus, "pending">;
  comment?: string;
}

/** Normalise form values into the API payload. */
export function toHandoverPayload(v: {
  task: string;
  to_user_id: string;
  summary: string;
  pending_items?: string;
  resources?: string;
}): HandoverPayload {
  return {
    task: v.task,
    to_user_id: v.to_user_id,
    summary: v.summary,
    pending_items: v.pending_items ?? "",
    resources: v.resources ?? "",
  };
}

export const handoversApi = {
  list: (params: HandoverListParams) =>
    apiClient.get<Paginated<Handover>>(API_ROUTES.handovers.list, { params }),
  get: (id: string) => apiClient.get<Handover>(API_ROUTES.handovers.detail(id)),
  create: (data: HandoverPayload) =>
    apiClient.post<Handover>(API_ROUTES.handovers.list, data),
  update: (id: string, data: HandoverPayload) =>
    apiClient.patch<Handover>(API_ROUTES.handovers.detail(id), data),
  remove: (id: string) =>
    apiClient.delete<void>(API_ROUTES.handovers.detail(id)),
  review: (id: string, data: HandoverReviewPayload) =>
    apiClient.post<Handover>(API_ROUTES.handovers.review(id), data),
};
