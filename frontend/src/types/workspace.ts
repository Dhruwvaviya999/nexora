/** Workspace types (mirror the backend serializers). */

import type { AuthUser } from "@/types/auth";

export type WorkspaceRole = "owner" | "admin" | "manager" | "member";

/** Roles that may review handovers and other approval flows. */
export const REVIEWER_ROLES: readonly WorkspaceRole[] = [
  "owner",
  "admin",
  "manager",
];

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string;
  owner: AuthUser;
  /** Current user's role in this workspace. */
  role: WorkspaceRole | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  user: AuthUser;
  role: WorkspaceRole;
  joined_at: string;
}
