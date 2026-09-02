"use client";

import * as React from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/shared/page-header";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { DataPagination } from "@/components/shared/data-pagination";
import { ActivityTimeline } from "@/components/activities/activity-timeline";
import { useActivities } from "@/hooks/use-activities";
import { useWorkspaceMembers } from "@/hooks/use-workspaces";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { downloadFile } from "@/lib/api/download";
import { ACTIVITY_ACTIONS } from "@/lib/activity";
import { API_ROUTES } from "@/lib/constants";
import { toDateOnly } from "@/lib/format";

import { PageContainer } from "@/components/layout/page-container";
const ALL = "all";

const RANGES = [
  { value: ALL, label: "All time", days: null },
  { value: "7", label: "Last 7 days", days: 7 },
  { value: "30", label: "Last 30 days", days: 30 },
  { value: "90", label: "Last 90 days", days: 90 },
] as const;

function dateFromForRange(range: string): string | undefined {
  const preset = RANGES.find((r) => r.value === range);
  if (!preset?.days) return undefined;
  const from = new Date();
  from.setDate(from.getDate() - preset.days);
  return toDateOnly(from);
}

export default function ActivityPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [action, setAction] = React.useState(ALL);
  const [actor, setActor] = React.useState(ALL);
  const [range, setRange] = React.useState<string>(ALL);
  const [page, setPage] = React.useState(1);
  const [exporting, setExporting] = React.useState(false);

  const { data: members } = useWorkspaceMembers(activeWorkspaceId ?? "");

  const filters = {
    workspace: activeWorkspaceId ?? undefined,
    action: action === ALL ? undefined : action,
    actor: actor === ALL ? undefined : actor,
    date_from: dateFromForRange(range),
  };
  const { data, isLoading } = useActivities({ ...filters, page });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  async function exportCsv() {
    setExporting(true);
    try {
      await downloadFile(API_ROUTES.activitiesExport, "audit-log.csv", filters);
      toast.success("Audit log exported");
    } catch {
      toast.error("Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <PageContainer size="md" className="space-y-6">
      <PageHeader
        title="Activity"
        description="The audit log of everything that happened in this workspace."
      >
        <Button variant="outline" onClick={exportCsv} disabled={exporting}>
          <Download className="size-4" />
          {exporting ? "Exporting…" : "Export CSV"}
        </Button>
      </PageHeader>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Select value={action} onValueChange={(v) => { setAction(v); setPage(1); }}>
          <SelectTrigger className="sm:w-48">
            <SelectValue placeholder="Action" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All actions</SelectItem>
            {ACTIVITY_ACTIONS.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={actor} onValueChange={(v) => { setActor(v); setPage(1); }}>
          <SelectTrigger className="sm:w-48">
            <SelectValue placeholder="Member" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All members</SelectItem>
            {members?.map((m) => (
              <SelectItem key={m.user.id} value={m.user.id}>
                {m.user.name || m.user.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={range} onValueChange={(v) => { setRange(v); setPage(1); }}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            {RANGES.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <ActivityTimeline activities={data?.results ?? []} isLoading={isLoading} />
      <DataPagination
        page={page}
        count={data?.count ?? 0}
        onPageChange={setPage}
      />
    </PageContainer>
  );
}
