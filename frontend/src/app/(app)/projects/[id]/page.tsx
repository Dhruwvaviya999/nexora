"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Loader2, Pencil, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { TasksTable } from "@/components/tasks/tasks-table";
import { DocumentsTable } from "@/components/documents/documents-table";
import { CollaborationTabs } from "@/components/comments/collaboration-tabs";
import { useProject } from "@/hooks/use-projects";
import { useTasks } from "@/hooks/use-tasks";
import { useDocuments } from "@/hooks/use-documents";
import { ROUTES } from "@/lib/constants";
import { formatDate } from "@/lib/format";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: project, isLoading } = useProject(id);
  const { data: tasks, isLoading: tasksLoading } = useTasks({
    workspace: project?.workspace,
    project: id,
  });
  const { data: documents, isLoading: docsLoading } = useDocuments({
    workspace: project?.workspace,
    project: id,
  });

  if (isLoading || !project) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title={project.name} description={project.description || "No description"}>
        <Button variant="outline" asChild>
          <Link href={ROUTES.editProject(project.id)}>
            <Pencil className="size-4" />
            Edit
          </Link>
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <StatusBadge status={project.status} />
        <span>·</span>
        <span>{project.task_count} tasks</span>
        <span>·</span>
        <span>Owner: {project.owner?.name || project.owner?.email || "—"}</span>
        <span>·</span>
        <span>Created {formatDate(project.created_at)}</span>
      </div>

      <Tabs defaultValue="tasks">
        <TabsList>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-4">
          <div className="flex justify-end">
            <Button size="sm" asChild>
              <Link href={`${ROUTES.newTask}?project=${project.id}`}>
                <Plus className="size-4" />
                New task
              </Link>
            </Button>
          </div>
          {tasksLoading ? (
            <TableSkeleton columns={4} />
          ) : tasks?.results.length ? (
            <TasksTable tasks={tasks.results} />
          ) : (
            <EmptyState title="No tasks in this project yet" />
          )}
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          <div className="flex justify-end">
            <Button size="sm" asChild>
              <Link href={`${ROUTES.newDocument}?project=${project.id}`}>
                <Plus className="size-4" />
                Upload
              </Link>
            </Button>
          </div>
          {docsLoading ? (
            <TableSkeleton columns={4} />
          ) : documents?.results.length ? (
            <DocumentsTable documents={documents.results} />
          ) : (
            <EmptyState title="No documents in this project yet" />
          )}
        </TabsContent>
      </Tabs>

      <CollaborationTabs targetType="project" targetId={project.id} />
    </div>
  );
}
