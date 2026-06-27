"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { workspacesApi } from "@/lib/api/workspaces";

function useInvalidateMembers(workspaceId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["workspaces", workspaceId, "members"] });
    qc.invalidateQueries({ queryKey: ["workspaces"] });
  };
}

export function useUpdateMemberRole(workspaceId: string) {
  const invalidate = useInvalidateMembers(workspaceId);
  return useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      workspacesApi.updateMemberRole(workspaceId, memberId, role),
    onSuccess: invalidate,
  });
}

export function useRemoveMember(workspaceId: string) {
  const invalidate = useInvalidateMembers(workspaceId);
  return useMutation({
    mutationFn: (memberId: string) =>
      workspacesApi.removeMember(workspaceId, memberId),
    onSuccess: invalidate,
  });
}

export function useTransferOwnership(workspaceId: string) {
  const invalidate = useInvalidateMembers(workspaceId);
  return useMutation({
    mutationFn: (userId: string) =>
      workspacesApi.transferOwnership(workspaceId, userId),
    onSuccess: invalidate,
  });
}
