"use client";

import * as React from "react";
import Link from "next/link";
import { FileText, FolderKanban, ListTodo, SearchIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { StatusBadge } from "@/components/shared/status-badge";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useProjects } from "@/hooks/use-projects";
import { useTasks } from "@/hooks/use-tasks";
import { useDocuments } from "@/hooks/use-documents";
import { ROUTES } from "@/lib/constants";

export default function SearchPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [query, setQuery] = React.useState("");
  const enabled = query.length >= 2;
  const ws = activeWorkspaceId ?? undefined;

  const projects = useProjects({ workspace: enabled ? ws : undefined, search: query });
  const tasks = useTasks({ workspace: enabled ? ws : undefined, search: query });
  const documents = useDocuments({ workspace: enabled ? ws : undefined, search: query });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const projectResults = projects.data?.results ?? [];
  const taskResults = tasks.data?.results ?? [];
  const documentResults = documents.data?.results ?? [];
  const hasResults =
    projectResults.length || taskResults.length || documentResults.length;

  return (
    <div className="space-y-6">
      <PageHeader title="Search" description="Search projects, tasks, and documents." />

      <SearchInput
        value={query}
        onSearch={setQuery}
        placeholder="Type at least 2 characters…"
        className="max-w-xl"
      />

      {!enabled ? (
        <EmptyState icon={SearchIcon} title="Start typing to search" />
      ) : !hasResults ? (
        <EmptyState icon={SearchIcon} title="No results" description={`Nothing matched "${query}".`} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader className="flex-row items-center gap-2">
              <FolderKanban className="size-4 text-muted-foreground" />
              <CardTitle className="text-base">Projects ({projectResults.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {projectResults.map((p) => (
                <Link
                  key={p.id}
                  href={ROUTES.project(p.id)}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
                >
                  <span className="truncate text-sm font-medium">{p.name}</span>
                  <StatusBadge status={p.status} />
                </Link>
              ))}
              {!projectResults.length && (
                <p className="px-2 text-sm text-muted-foreground">No projects.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center gap-2">
              <ListTodo className="size-4 text-muted-foreground" />
              <CardTitle className="text-base">Tasks ({taskResults.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {taskResults.map((t) => (
                <Link
                  key={t.id}
                  href={ROUTES.task(t.id)}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
                >
                  <span className="truncate text-sm font-medium">{t.title}</span>
                  <PriorityBadge priority={t.priority} />
                </Link>
              ))}
              {!taskResults.length && (
                <p className="px-2 text-sm text-muted-foreground">No tasks.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center gap-2">
              <FileText className="size-4 text-muted-foreground" />
              <CardTitle className="text-base">Documents ({documentResults.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {documentResults.map((d) => (
                <Link
                  key={d.id}
                  href={ROUTES.document(d.id)}
                  className="block truncate rounded-md px-2 py-1.5 text-sm font-medium hover:bg-accent"
                >
                  {d.title}
                </Link>
              ))}
              {!documentResults.length && (
                <p className="px-2 text-sm text-muted-foreground">No documents.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
