"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TaskForm } from "@/components/tasks/task-form";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useCreateTask } from "@/hooks/use-tasks";
import { toTaskPayload } from "@/lib/api/tasks";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { TaskValues } from "@/lib/validations/task";

function NewTaskInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { activeWorkspaceId } = useWorkspaceContext();
  const createTask = useCreateTask();

  if (!activeWorkspaceId) return <NoWorkspace />;

  async function handleSubmit(values: TaskValues) {
    try {
      const task = await createTask.mutateAsync(toTaskPayload(values));
      toast.success("Task created");
      router.replace(ROUTES.task(task.id));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <PageHeader title="New task" description="Add a task to a project." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Task details</CardTitle>
        </CardHeader>
        <CardContent>
          <TaskForm
            workspaceId={activeWorkspaceId}
            defaultValues={{ project: searchParams.get("project") ?? "" }}
            submitLabel="Create task"
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </div>
  );
}

export default function NewTaskPage() {
  return (
    <Suspense fallback={null}>
      <NewTaskInner />
    </Suspense>
  );
}
