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
import { ProjectForm } from "@/components/projects/project-form";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useCreateProject } from "@/hooks/use-projects";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { ProjectValues } from "@/lib/validations/project";

export default function NewProjectPage() {
  const router = useRouter();
  const { activeWorkspaceId } = useWorkspaceContext();
  const createProject = useCreateProject();

  if (!activeWorkspaceId) return <NoWorkspace />;

  async function handleSubmit(values: ProjectValues) {
    try {
      const project = await createProject.mutateAsync({
        ...values,
        workspace: activeWorkspaceId as string,
      });
      toast.success("Project created");
      router.replace(ROUTES.project(project.id));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <PageHeader title="New project" description="Create a project in this workspace." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Project details</CardTitle>
          <CardDescription>A slug is generated automatically.</CardDescription>
        </CardHeader>
        <CardContent>
          <ProjectForm submitLabel="Create project" onSubmit={handleSubmit} />
        </CardContent>
      </Card>
    </div>
  );
}
