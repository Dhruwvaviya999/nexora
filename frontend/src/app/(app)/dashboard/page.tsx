"use client";

import Link from "next/link";
import {
  ArrowLeftRight,
  CheckCircle2,
  Clock,
  FileText,
  FolderKanban,
  ListTodo,
  Plus,
  TriangleAlert,
  UserCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useDashboard } from "@/hooks/use-dashboard";
import { ROUTES } from "@/lib/constants";
import { formatDate } from "@/lib/format";

export default function DashboardPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: wsLoading } =
    useWorkspaceContext();
  const { data, isLoading } = useDashboard(activeWorkspaceId ?? undefined);

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const stats = data?.stats;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={
          activeWorkspace
            ? `Overview of ${activeWorkspace.name}.`
            : "Workspace overview."
        }
      >
        <Button asChild>
          <Link href={ROUTES.newProject}>
            <Plus className="size-4" />
            New project
          </Link>
        </Button>
      </PageHeader>

      {isLoading || !stats ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total projects" value={stats.total_projects} icon={FolderKanban} />
          <StatCard label="Active projects" value={stats.active_projects} icon={FolderKanban} />
          <StatCard label="Archived" value={stats.archived_projects} icon={FolderKanban} />
          <StatCard label="Documents" value={stats.total_documents} icon={FileText} />
          <StatCard label="Total tasks" value={stats.total_tasks} icon={ListTodo} />
          <StatCard label="Pending tasks" value={stats.pending_tasks} icon={Clock} />
          <StatCard label="Completed" value={stats.completed_tasks} icon={CheckCircle2} />
          <StatCard
            label="Overdue"
            value={stats.overdue_tasks}
            icon={TriangleAlert}
            accent={stats.overdue_tasks ? "bg-destructive/15 text-destructive" : undefined}
          />
          <StatCard label="My open tasks" value={stats.my_tasks} icon={UserCheck} />
          <StatCard
            label="Pending handovers"
            value={stats.pending_handovers}
            icon={ArrowLeftRight}
            accent={
              stats.pending_handovers
                ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                : undefined
            }
          />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Recent projects</CardTitle>
            <Link href={ROUTES.projects} className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {!data?.recent_projects.length ? (
              <EmptyState title="No projects yet" />
            ) : (
              data.recent_projects.map((p) => (
                <Link
                  key={p.id}
                  href={ROUTES.project(p.id)}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
                >
                  <span className="flex items-center gap-2 truncate">
                    <span className="size-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                    <span className="truncate text-sm font-medium">{p.name}</span>
                  </span>
                  <StatusBadge status={p.status} />
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Recent tasks</CardTitle>
            <Link href={ROUTES.tasks} className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {!data?.recent_tasks.length ? (
              <EmptyState title="No tasks yet" />
            ) : (
              data.recent_tasks.map((t) => (
                <Link
                  key={t.id}
                  href={ROUTES.task(t.id)}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
                >
                  <span className="truncate text-sm font-medium">{t.title}</span>
                  <PriorityBadge priority={t.priority} />
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Recent documents</CardTitle>
            <Link href={ROUTES.documents} className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {!data?.recent_documents.length ? (
              <EmptyState title="No documents yet" />
            ) : (
              data.recent_documents.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5"
                >
                  <span className="flex items-center gap-2 truncate">
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm font-medium">{d.title}</span>
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(d.created_at)}
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Pending handovers</CardTitle>
            <Link href={ROUTES.handovers} className="text-sm text-muted-foreground hover:text-foreground">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {!data?.pending_handovers.length ? (
              <EmptyState title="Nothing awaiting review" />
            ) : (
              data.pending_handovers.map((h) => (
                <Link
                  key={h.id}
                  href={ROUTES.handover(h.id)}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <ArrowLeftRight className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm font-medium">{h.task_title}</span>
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {h.to_user?.name || h.to_user?.email || "—"}
                  </span>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
