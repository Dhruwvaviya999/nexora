import type { AuthUser } from "@/types/auth";
import type { WorkspaceRole } from "@/types/workspace";

export type InvitationStatus =
  | "pending"
  | "accepted"
  | "rejected"
  | "expired"
  | "cancelled";

/** Roles that can be invited (owner is never invitable). */
export type InvitableRole = Exclude<WorkspaceRole, "owner">;

export interface Invitation {
  id: string;
  workspace: string;
  workspace_name: string;
  email: string;
  role: WorkspaceRole;
  status: InvitationStatus;
  token: string;
  invited_by: AuthUser;
  expires_at: string;
  created_at: string;
}
