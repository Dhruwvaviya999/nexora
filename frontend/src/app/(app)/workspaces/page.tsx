"use client";

import Link from "next/link";
import { Loader2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { WorkspaceCard } from "@/components/workspaces/workspace-card";
import { useWorkspaces } from "@/hooks/use-workspaces";
import { ROUTES } from "@/lib/constants";

export default function WorkspacesPage() {
  const { data, isLoading, isError } = useWorkspaces();
  const workspaces = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Workspaces</h1>
          <p className="text-sm text-muted-foreground">
            Workspaces you own or belong to.
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.newWorkspace}>
            <Plus className="size-4" />
            New workspace
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : isError ? (
        <p className="py-16 text-center text-sm text-destructive">
          Failed to load workspaces.
        </p>
      ) : workspaces.length === 0 ? (
        <div className="rounded-lg border border-dashed py-16 text-center">
          <p className="text-sm text-muted-foreground">
            You don&apos;t have any workspaces yet.
          </p>
          <Button asChild className="mt-4">
            <Link href={ROUTES.newWorkspace}>Create your first workspace</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => (
            <WorkspaceCard key={workspace.id} workspace={workspace} />
          ))}
        </div>
      )}
    </div>
  );
}
