"use client";

import * as React from "react";
import Link from "next/link";
import { ListTodo, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { DataPagination } from "@/components/shared/data-pagination";
import { TasksTable } from "@/components/tasks/tasks-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useTasks } from "@/hooks/use-tasks";
import { TASK_PRIORITIES, TASK_STATUSES, ROUTES } from "@/lib/constants";

const ALL = "all";

export default function TasksPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState(ALL);
  const [priority, setPriority] = React.useState(ALL);
  const [page, setPage] = React.useState(1);

  const { data, isLoading } = useTasks({
    workspace: activeWorkspaceId ?? undefined,
    search: search || undefined,
    status: status === ALL ? undefined : status,
    priority: priority === ALL ? undefined : priority,
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const tasks = data?.results ?? [];

  return (
    <div className="space-y-5">
      <PageHeader title="Tasks" description="Track work across your projects.">
        <Button asChild>
          <Link href={ROUTES.newTask}>
            <Plus className="size-4" />
            New task
          </Link>
        </Button>
      </PageHeader>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchInput
          value={search}
          onSearch={(v) => {
            setSearch(v);
            setPage(1);
          }}
          placeholder="Search tasks…"
          className="sm:max-w-xs sm:flex-1"
        />
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {TASK_STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priority} onValueChange={(v) => { setPriority(v); setPage(1); }}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All priorities</SelectItem>
            {TASK_PRIORITIES.map((p) => (
              <SelectItem key={p.value} value={p.value}>
                {p.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <TableSkeleton columns={5} />
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={ListTodo}
          title="No tasks found"
          description="Create a task to start tracking work."
          action={
            <Button asChild>
              <Link href={ROUTES.newTask}>New task</Link>
            </Button>
          }
        />
      ) : (
        <>
          <TasksTable tasks={tasks} />
          <DataPagination page={page} count={data?.count ?? 0} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
