import Link from "next/link";
import { Users } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ROUTES } from "@/lib/constants";
import type { Workspace } from "@/types/workspace";

export function WorkspaceCard({ workspace }: { workspace: Workspace }) {
  return (
    <Link href={ROUTES.workspaceSettings(workspace.id)} className="block">
      <Card className="h-full transition-colors hover:border-foreground/20">
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">{workspace.name}</CardTitle>
            {workspace.role && (
              <span className="rounded-full border px-2 py-0.5 text-xs capitalize text-muted-foreground">
                {workspace.role}
              </span>
            )}
          </div>
          <CardDescription className="line-clamp-2">
            {workspace.description || "No description"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Users className="size-4" />
          {workspace.member_count}{" "}
          {workspace.member_count === 1 ? "member" : "members"}
        </CardContent>
      </Card>
    </Link>
  );
}
