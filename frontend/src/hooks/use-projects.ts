"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { projectsApi, type ProjectListParams } from "@/lib/api/projects";
import type { ProjectValues } from "@/lib/validations/project";

const KEYS = {
  all: ["projects"] as const,
  list: (params: ProjectListParams) => ["projects", "list", params] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects(params: ProjectListParams) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => projectsApi.list(params),
    enabled: !!params.workspace,
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => projectsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectValues & { workspace: string }) =>
      projectsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<ProjectValues>) => projectsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all });
      qc.invalidateQueries({ queryKey: KEYS.detail(id) });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projectsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useArchiveProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived ? projectsApi.archive(id) : projectsApi.restore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}
