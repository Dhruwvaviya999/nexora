"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Archive,
  ArchiveRestore,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useArchiveProject, useDeleteProject } from "@/hooks/use-projects";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";
import { ROUTES } from "@/lib/constants";
import type { Project } from "@/types/project";

export function ProjectsTable({ projects }: { projects: Project[] }) {
  const router = useRouter();
  const deleteProject = useDeleteProject();
  const archiveProject = useArchiveProject();
  const [target, setTarget] = React.useState<Project | null>(null);

  async function onDelete() {
    if (!target) return;
    try {
      await deleteProject.mutateAsync(target.id);
      toast.success("Project deleted");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  async function onToggleArchive(p: Project) {
    try {
      await archiveProject.mutateAsync({ id: p.id, archived: !p.archived });
      toast.success(p.archived ? "Project restored" : "Project archived");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Status</TableHead>
            <TableHead className="hidden md:table-cell">Tasks</TableHead>
            <TableHead className="hidden lg:table-cell">Updated</TableHead>
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {projects.map((project) => (
            <TableRow
              key={project.id}
              className="cursor-pointer"
              onClick={() => router.push(ROUTES.project(project.id))}
            >
              <TableCell>
                <div className="flex items-center gap-2">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: project.color || "#6366f1" }}
                  />
                  <span className="font-medium">{project.name}</span>
                  {project.archived && (
                    <span className="text-xs text-muted-foreground">(archived)</span>
                  )}
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <StatusBadge status={project.status} />
              </TableCell>
              <TableCell className="hidden md:table-cell text-muted-foreground">
                {project.task_count}
              </TableCell>
              <TableCell className="hidden lg:table-cell text-muted-foreground">
                {formatDate(project.updated_at)}
              </TableCell>
              <TableCell onClick={(e) => e.stopPropagation()}>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="size-8">
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => router.push(ROUTES.editProject(project.id))}
                    >
                      <Pencil className="size-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onToggleArchive(project)}>
                      {project.archived ? (
                        <>
                          <ArchiveRestore className="size-4" />
                          Restore
                        </>
                      ) : (
                        <>
                          <Archive className="size-4" />
                          Archive
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      variant="destructive"
                      onClick={() => setTarget(project)}
                    >
                      <Trash2 className="size-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={!!target}
        onOpenChange={(o) => !o && setTarget(null)}
        title="Delete project?"
        description={
          target
            ? `"${target.name}" and its tasks will be permanently removed.`
            : ""
        }
        onConfirm={onDelete}
      />
    </div>
  );
}
