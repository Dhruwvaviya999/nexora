"use client";

import * as React from "react";
import Link from "next/link";
import { FileText, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { DataPagination } from "@/components/shared/data-pagination";
import { DocumentsTable } from "@/components/documents/documents-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useDocuments } from "@/hooks/use-documents";
import { ROUTES } from "@/lib/constants";

export default function DocumentsPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(1);

  const { data, isLoading } = useDocuments({
    workspace: activeWorkspaceId ?? undefined,
    search: search || undefined,
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const documents = data?.results ?? [];

  return (
    <div className="space-y-5">
      <PageHeader title="Documents" description="Files stored in this workspace.">
        <Button asChild>
          <Link href={ROUTES.newDocument}>
            <Plus className="size-4" />
            Upload
          </Link>
        </Button>
      </PageHeader>

      <SearchInput
        value={search}
        onSearch={(v) => {
          setSearch(v);
          setPage(1);
        }}
        placeholder="Search documents…"
        className="sm:max-w-xs"
      />

      {isLoading ? (
        <TableSkeleton columns={4} />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents found"
          description="Upload a file to get started."
          action={
            <Button asChild>
              <Link href={ROUTES.newDocument}>Upload document</Link>
            </Button>
          }
        />
      ) : (
        <>
          <DocumentsTable documents={documents} />
          <DataPagination page={page} count={data?.count ?? 0} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
