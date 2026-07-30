"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeftRight, ClipboardCheck, Plus } from "lucide-react";

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
import { HandoversTable } from "@/components/handovers/handovers-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useHandovers } from "@/hooks/use-handovers";
import { HANDOVER_STATUSES, ROUTES } from "@/lib/constants";
import { REVIEWER_ROLES } from "@/types/workspace";

const ALL = "all";

export default function HandoversPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: wsLoading } =
    useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState(ALL);
  const [page, setPage] = React.useState(1);

  const { data, isLoading } = useHandovers({
    workspace: activeWorkspaceId ?? undefined,
    search: search || undefined,
    status: status === ALL ? undefined : status,
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const handovers = data?.results ?? [];
  const canReview =
    !!activeWorkspace?.role && REVIEWER_ROLES.includes(activeWorkspace.role);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Handovers"
        description="The history of task handovers in this workspace."
      >
        {canReview ? (
          <Button variant="outline" asChild>
            <Link href={ROUTES.handoverReviews}>
              <ClipboardCheck className="size-4" />
              Review queue
            </Link>
          </Button>
        ) : null}
        <Button asChild>
          <Link href={ROUTES.newHandover}>
            <Plus className="size-4" />
            New handover
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
          placeholder="Search handovers…"
          className="sm:max-w-xs sm:flex-1"
        />
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {HANDOVER_STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <TableSkeleton columns={6} />
      ) : handovers.length === 0 ? (
        <EmptyState
          icon={ArrowLeftRight}
          title="No handovers found"
          description="Submit a handover when a task needs to change hands."
          action={
            <Button asChild>
              <Link href={ROUTES.newHandover}>New handover</Link>
            </Button>
          }
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
