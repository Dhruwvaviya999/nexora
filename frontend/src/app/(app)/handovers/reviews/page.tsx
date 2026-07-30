"use client";

import * as React from "react";
import { ClipboardCheck, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { DataPagination } from "@/components/shared/data-pagination";
import { HandoversTable } from "@/components/handovers/handovers-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useHandovers } from "@/hooks/use-handovers";
import { REVIEWER_ROLES } from "@/types/workspace";

export default function HandoverReviewsPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: wsLoading } =
    useWorkspaceContext();
  const [page, setPage] = React.useState(1);

  const canReview =
    !!activeWorkspace?.role && REVIEWER_ROLES.includes(activeWorkspace.role);

  const { data, isLoading } = useHandovers({
    workspace: canReview ? activeWorkspaceId ?? undefined : undefined,
    status: "pending",
    ordering: "created_at", // oldest first — review in submission order
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  if (!wsLoading && activeWorkspace && !canReview) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Manager access needed"
        description="Only workspace owners, admins, and managers can review handovers."
      />
    );
  }

  const handovers = data?.results ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Handover reviews"
        description="Pending handovers awaiting your decision, oldest first."
      />

      {isLoading ? (
        <TableSkeleton columns={6} />
      ) : handovers.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title="All caught up"
          description="There are no handovers waiting for review."
        />
      ) : (
        <>
          <HandoversTable handovers={handovers} />
          <DataPagination
            page={page}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
