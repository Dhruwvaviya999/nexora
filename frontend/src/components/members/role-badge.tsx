import { Badge } from "@/components/ui/badge";
import type { WorkspaceRole } from "@/types/workspace";

const VARIANT: Record<WorkspaceRole, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export function RoleBadge({ role }: { role: WorkspaceRole }) {
  return (
    <Badge variant={VARIANT[role]} className="capitalize">
      {role}
    </Badge>
  );
}
