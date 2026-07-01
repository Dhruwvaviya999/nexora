"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { WorkspaceForm } from "@/components/workspaces/workspace-form";
import { useCreateWorkspace } from "@/hooks/use-workspaces";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { WorkspaceValues } from "@/lib/validations/workspace";

export default function NewWorkspacePage() {
  const router = useRouter();
  const createWorkspace = useCreateWorkspace();

  async function handleSubmit(values: WorkspaceValues) {
    try {
      const workspace = await createWorkspace.mutateAsync(values);
      toast.success("Workspace created");
      router.replace(ROUTES.workspaceSettings(workspace.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Create a workspace</CardTitle>
          <CardDescription>
            Workspaces group your projects, documents, and team.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <WorkspaceForm submitLabel="Create workspace" onSubmit={handleSubmit} />
        </CardContent>
      </Card>
    </div>
  );
}
