"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Loader2, Pencil } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { CollaborationTabs } from "@/components/comments/collaboration-tabs";
import { useTask, useUpdateTask } from "@/hooks/use-tasks";
import { toTaskPayload } from "@/lib/api/tasks";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";
import { ROUTES, TASK_STATUSES } from "@/lib/constants";

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="text-sm">{children}</div>
    </div>
  );
}

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: task, isLoading } = useTask(id);
  const updateTask = useUpdateTask(id);

  if (isLoading || !task) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  async function changeStatus(status: string) {
    if (!task) return;
    try {
      await updateTask.mutateAsync(
        toTaskPayload({
          project: task.project,
          title: task.title,
          description: task.description,
          status,
          priority: task.priority,
          assignee_id: task.assignee?.id ?? "",
          due_date: task.due_date ?? "",
          start_date: task.start_date ?? "",
          estimated_hours: task.estimated_hours ?? "",
          labels: task.labels,
        })
      );
      toast.success("Status updated");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <PageHeader title={task.title} description={task.description || "No description"}>
        <Button variant="outline" asChild>
          <Link href={ROUTES.editTask(task.id)}>
            <Pencil className="size-4" />
            Edit
          </Link>
        </Button>
      </PageHeader>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Details</CardTitle>
          <Select value={task.status} onValueChange={changeStatus}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TASK_STATUSES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="grid gap-5 sm:grid-cols-2">
          <Detail label="Status">
            <StatusBadge status={task.status} />
          </Detail>
          <Detail label="Priority">
            <PriorityBadge priority={task.priority} />
          </Detail>
          <Detail label="Assignee">
            {task.assignee ? (
              <span className="flex items-center gap-2">
                <Avatar className="size-6">
                  <AvatarImage src={task.assignee.avatar || undefined} />
                  <AvatarFallback className="text-xs">
                    {(task.assignee.name || task.assignee.email).charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {task.assignee.name || task.assignee.email}
              </span>
            ) : (
              <span className="text-muted-foreground">Unassigned</span>
            )}
          </Detail>
          <Detail label="Reporter">
            {task.reporter?.name || task.reporter?.email || "—"}
          </Detail>
          <Detail label="Due date">{formatDate(task.due_date)}</Detail>
          <Detail label="Start date">{formatDate(task.start_date)}</Detail>
          <Detail label="Estimated hours">{task.estimated_hours ?? "—"}</Detail>
          <Detail label="Labels">
            {task.labels.length ? (
              <div className="flex flex-wrap gap-1">
                {task.labels.map((l) => (
                  <Badge key={l} variant="secondary">
                    {l}
                  </Badge>
                ))}
              </div>
            ) : (
              "—"
            )}
          </Detail>
        </CardContent>
        <Separator />
        <CardContent className="pt-4 text-xs text-muted-foreground">
          Created {formatDate(task.created_at)} · Updated {formatDate(task.updated_at)}
        </CardContent>
      </Card>

      <CollaborationTabs targetType="task" targetId={task.id} />
    </div>
  );
}
