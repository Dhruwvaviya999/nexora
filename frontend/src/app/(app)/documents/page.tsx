"use client";

import * as React from "react";
import Link from "next/link";
import { FileText, Plus } from "lucide-react";

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
import { DocumentsTable } from "@/components/documents/documents-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useDocuments } from "@/hooks/use-documents";
import { useProjects } from "@/hooks/use-projects";
import { ROUTES } from "@/lib/constants";

const ALL = "all";

export default function DocumentsPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const [project, setProject] = React.useState(ALL);
  const [page, setPage] = React.useState(1);

  const { data: projectsData } = useProjects({
    workspace: activeWorkspaceId ?? undefined,
  });

  const { data, isLoading } = useDocuments({
    workspace: activeWorkspaceId ?? undefined,
    search: search || undefined,
    project: project === ALL ? undefined : project,
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const documents = data?.results ?? [];
  const projects = projectsData?.results ?? [];

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

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchInput
          value={search}
          onSearch={(v) => {
            setSearch(v);
            setPage(1);
          }}
          placeholder="Search documents…"
          className="sm:max-w-xs sm:flex-1"
        />
        <Select value={project} onValueChange={(v) => { setProject(v); setPage(1); }}>
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder="Project" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

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
