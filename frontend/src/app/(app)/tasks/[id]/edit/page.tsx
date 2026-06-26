"use client";

import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TaskForm } from "@/components/tasks/task-form";
import { PageHeader } from "@/components/shared/page-header";
import { useTask, useUpdateTask } from "@/hooks/use-tasks";
import { toTaskPayload } from "@/lib/api/tasks";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { TaskValues } from "@/lib/validations/task";

export default function EditTaskPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: task, isLoading } = useTask(id);
  const updateTask = useUpdateTask(id);

  if (isLoading || !task) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  async function handleSubmit(values: TaskValues) {
    try {
      await updateTask.mutateAsync(toTaskPayload(values));
      toast.success("Task updated");
      router.replace(ROUTES.task(id));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <PageHeader title="Edit task" />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Task details</CardTitle>
        </CardHeader>
        <CardContent>
          <TaskForm
            workspaceId={task.workspace}
            defaultValues={{
              project: task.project,
              title: task.title,
              description: task.description,
              status: task.status,
              priority: task.priority,
              assignee_id: task.assignee?.id ?? "",
              due_date: task.due_date ?? "",
              start_date: task.start_date ?? "",
              estimated_hours: task.estimated_hours ?? "",
              labels: task.labels,
            }}
            submitLabel="Save changes"
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </div>
  );
}
