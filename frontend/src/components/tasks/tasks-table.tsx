"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/shared/status-badge";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useDeleteTask } from "@/hooks/use-tasks";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate, isPast } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import type { Task } from "@/types/task";

export function TasksTable({ tasks }: { tasks: Task[] }) {
  const router = useRouter();
  const deleteTask = useDeleteTask();
  const [target, setTarget] = React.useState<Task | null>(null);

  async function onDelete() {
    if (!target) return;
    try {
      await deleteTask.mutateAsync(target.id);
      toast.success("Task deleted");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  const overdueStatuses = ["todo", "in_progress", "review"];

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead className="hidden sm:table-cell">Status</TableHead>
            <TableHead className="hidden md:table-cell">Priority</TableHead>
            <TableHead className="hidden lg:table-cell">Assignee</TableHead>
            <TableHead className="hidden lg:table-cell">Due</TableHead>
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => {
            const overdue =
              isPast(task.due_date) && overdueStatuses.includes(task.status);
            return (
              <TableRow
                key={task.id}
                className="cursor-pointer"
                onClick={() => router.push(ROUTES.task(task.id))}
              >
                <TableCell className="font-medium">{task.title}</TableCell>
                <TableCell className="hidden sm:table-cell">
                  <StatusBadge status={task.status} />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <PriorityBadge priority={task.priority} />
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {task.assignee ? (
                    <div className="flex items-center gap-2">
                      <Avatar className="size-6">
                        <AvatarImage src={task.assignee.avatar || undefined} />
                        <AvatarFallback className="text-xs">
                          {(task.assignee.name || task.assignee.email)
                            .charAt(0)
                            .toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-sm text-muted-foreground">
                        {task.assignee.name || task.assignee.email}
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">Unassigned</span>
                  )}
                </TableCell>
                <TableCell
                  className={cn(
                    "hidden lg:table-cell text-sm",
                    overdue ? "text-destructive" : "text-muted-foreground"
                  )}
                >
                  {formatDate(task.due_date)}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="size-8">
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => router.push(ROUTES.editTask(task.id))}
                      >
                        <Pencil className="size-4" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        variant="destructive"
                        onClick={() => setTarget(task)}
                      >
                        <Trash2 className="size-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={!!target}
        onOpenChange={(o) => !o && setTarget(null)}
        title="Delete task?"
        description={target ? `"${target.title}" will be permanently removed.` : ""}
        onConfirm={onDelete}
      />
    </div>
  );
}
