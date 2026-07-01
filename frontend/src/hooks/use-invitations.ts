"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  invitationsApi,
  type CreateInvitationInput,
} from "@/lib/api/invitations";

const KEYS = {
  workspace: (id: string) => ["invitations", "workspace", id] as const,
  mine: ["invitations", "mine"] as const,
};

export function useWorkspaceInvitations(workspaceId: string) {
  return useQuery({
    queryKey: KEYS.workspace(workspaceId),
    queryFn: () => invitationsApi.forWorkspace(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useMyInvitations() {
  return useQuery({
    queryKey: KEYS.mine,
    queryFn: () => invitationsApi.mine(),
  });
}

export function useCreateInvitation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateInvitationInput) => invitationsApi.create(input),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.workspace(workspaceId) }),
  });
}

export function useCancelInvitation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => invitationsApi.cancel(token),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.workspace(workspaceId) }),
  });
}

export function useResendInvitation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => invitationsApi.resend(token),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: KEYS.workspace(workspaceId) }),
  });
}

export function useAcceptInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => invitationsApi.accept(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.mine });
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useRejectInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => invitationsApi.reject(token),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.mine }),
  });
}
