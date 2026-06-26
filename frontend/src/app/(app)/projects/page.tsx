"use client";

import * as React from "react";
import Link from "next/link";
import { FolderKanban, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { DataPagination } from "@/components/shared/data-pagination";
import { ProjectsTable } from "@/components/projects/projects-table";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useProjects } from "@/hooks/use-projects";
import { PROJECT_STATUSES, ROUTES } from "@/lib/constants";

const ALL = "all";

export default function ProjectsPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<string>(ALL);
  const [archived, setArchived] = React.useState(false);
  const [page, setPage] = React.useState(1);

  const { data, isLoading } = useProjects({
    workspace: activeWorkspaceId ?? undefined,
    search: search || undefined,
    status: status === ALL ? undefined : status,
    archived,
    page,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const projects = data?.results ?? [];

  return (
    <div className="space-y-5">
      <PageHeader title="Projects" description="Organise work into projects.">
        <Button asChild>
          <Link href={ROUTES.newProject}>
            <Plus className="size-4" />
            New project
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
          placeholder="Search projects…"
          className="sm:max-w-xs sm:flex-1"
        />
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {PROJECT_STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <Switch
            id="archived"
            checked={archived}
            onCheckedChange={(v) => {
              setArchived(v);
              setPage(1);
            }}
          />
          <Label htmlFor="archived" className="text-sm text-muted-foreground">
            Archived
          </Label>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton columns={4} />
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects found"
          description="Create your first project to get started."
          action={
            <Button asChild>
              <Link href={ROUTES.newProject}>New project</Link>
            </Button>
          }
        />
      ) : (
        <>
          <ProjectsTable projects={projects} />
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
