"use client";

import { format, parseISO } from "date-fns";
import {
  ArrowLeftRight,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { BarChart, GroupedBarChart, HBarChart } from "@/components/charts/charts";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useAnalytics } from "@/hooks/use-analytics";
import { TASK_PRIORITIES, TASK_STATUSES } from "@/lib/constants";

export default function AnalyticsPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: wsLoading } =
    useWorkspaceContext();
  const { data, isLoading } = useAnalytics(activeWorkspaceId ?? undefined);

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Analytics" description="Workspace trends and workload." />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-72 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // Fixed display order for the enum axes (API rows are unordered).
  const statusData = TASK_STATUSES.map((s) => ({
    label: s.label,
    value: data.task_status.find((r) => r.status === s.value)?.count ?? 0,
  }));
  const priorityData = TASK_PRIORITIES.map((p) => ({
    label: p.label,
    value: data.task_priority.find((r) => r.priority === p.value)?.count ?? 0,
  }));
  const weeklyData = data.weekly.map((w) => ({
    label: format(parseISO(w.week_start), "MMM d"),
    a: w.created,
    b: w.completed,
  }));
  const workloadData = data.workload.map((w) => ({
    label: w.name,
    value: w.count,
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description={
          activeWorkspace
            ? `Trends and workload for ${activeWorkspace.name}.`
            : "Workspace trends and workload."
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Pending handovers"
          value={data.handovers.pending}
          icon={ArrowLeftRight}
        />
        <StatCard
          label="Approved handovers"
          value={data.handovers.approved}
          icon={CheckCircle2}
        />
        <StatCard
          label="Rejected handovers"
          value={data.handovers.rejected}
          icon={XCircle}
        />
        <StatCard
          label="Avg. review time"
          value={
            data.handovers.avg_review_hours === null
              ? "—"
              : `${data.handovers.avg_review_hours}h`
          }
          icon={Clock}
          hint="From submission to decision"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Tasks created vs completed (last 8 weeks)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <GroupedBarChart
              data={weeklyData}
              seriesLabels={["Created", "Completed"]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Open tasks per member</CardTitle>
          </CardHeader>
          <CardContent>
            {workloadData.length ? (
              <HBarChart data={workloadData} />
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No assigned open tasks.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tasks by status</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart data={statusData} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tasks by priority</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart data={priorityData} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
