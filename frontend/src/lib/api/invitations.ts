import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { InvitableRole, Invitation } from "@/types/invitation";

export interface CreateInvitationInput {
  workspace: string;
  email: string;
  role: InvitableRole;
}

export const invitationsApi = {
  /** Invitations for a workspace I administer. */
  forWorkspace: (workspace: string) =>
    apiClient.get<Paginated<Invitation>>(API_ROUTES.invitations.list, {
      params: { workspace },
    }),

  /** Pending invitations addressed to me. */
  mine: () =>
    apiClient.get<Paginated<Invitation>>(API_ROUTES.invitations.list, {
      params: { mine: "true", status: "pending" },
    }),

  create: (input: CreateInvitationInput) =>
    apiClient.post<Invitation>(API_ROUTES.invitations.list, input),

  accept: (token: string) =>
    apiClient.post<Invitation>(API_ROUTES.invitations.accept(token)),

  reject: (token: string) =>
    apiClient.post<Invitation>(API_ROUTES.invitations.reject(token)),

  resend: (token: string) =>
    apiClient.post<Invitation>(API_ROUTES.invitations.resend(token)),

  cancel: (token: string) =>
    apiClient.delete<void>(API_ROUTES.invitations.detail(token)),
};
