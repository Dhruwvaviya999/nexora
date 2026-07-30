"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  handoversApi,
  type HandoverListParams,
  type HandoverPayload,
  type HandoverReviewPayload,
} from "@/lib/api/handovers";

const KEYS = {
  all: ["handovers"] as const,
  list: (params: HandoverListParams) => ["handovers", "list", params] as const,
  detail: (id: string) => ["handovers", id] as const,
};

export function useHandovers(params: HandoverListParams) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => handoversApi.list(params),
    enabled: !!params.workspace,
  });
}

export function useHandover(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => handoversApi.get(id),
    enabled: !!id,
  });
}

export function useCreateHandover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HandoverPayload) => handoversApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateHandover(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HandoverPayload) => handoversApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all });
      qc.invalidateQueries({ queryKey: KEYS.detail(id) });
    },
  });
}

export function useDeleteHandover() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => handoversApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useReviewHandover(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: HandoverReviewPayload) => handoversApi.review(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all });
      qc.invalidateQueries({ queryKey: KEYS.detail(id) });
      // Approval reassigns the underlying task.
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}
