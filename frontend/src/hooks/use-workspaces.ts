"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { workspacesApi } from "@/lib/api/workspaces";
import type { WorkspaceValues } from "@/lib/validations/workspace";

const KEYS = {
  all: ["workspaces"] as const,
  detail: (id: string) => ["workspaces", id] as const,
  members: (id: string) => ["workspaces", id, "members"] as const,
};

export function useWorkspaces() {
  return useQuery({
    queryKey: KEYS.all,
    queryFn: () => workspacesApi.list(),
  });
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => workspacesApi.get(id),
    enabled: !!id,
  });
}

export function useWorkspaceMembers(id: string) {
  return useQuery({
    queryKey: KEYS.members(id),
    queryFn: () => workspacesApi.members(id),
    enabled: !!id,
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkspaceValues) => workspacesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.all });
    },
  });
}

export function useUpdateWorkspace(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<WorkspaceValues>) =>
      workspacesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.all });
      queryClient.invalidateQueries({ queryKey: KEYS.detail(id) });
    },
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workspacesApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEYS.all });
    },
  });
}
