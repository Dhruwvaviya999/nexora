"use client";

import { Building2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { cn } from "@/lib/utils";

/** Shows which workspace the assistant is scoped to (no cross-workspace data). */
export function WorkspaceContextBadge({ className }: { className?: string }) {
  const { activeWorkspace } = useWorkspaceContext();
  if (!activeWorkspace) return null;
  return (
    <Badge variant="outline" className={cn("gap-1 font-normal", className)}>
      <Building2 className="size-3" />
      {activeWorkspace.name}
    </Badge>
  );
}
