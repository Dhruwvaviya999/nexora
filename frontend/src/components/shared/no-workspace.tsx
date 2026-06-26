import Link from "next/link";
import { Building2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { ROUTES } from "@/lib/constants";

/** Shown on workspace-scoped pages when the user has no active workspace. */
export function NoWorkspace() {
  return (
    <EmptyState
      icon={Building2}
      title="No workspace selected"
      description="Create a workspace to start adding projects, tasks, and documents."
      action={
        <Button asChild>
          <Link href={ROUTES.newWorkspace}>Create workspace</Link>
        </Button>
      }
    />
  );
}
