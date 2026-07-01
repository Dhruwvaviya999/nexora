"use client";

import * as React from "react";
import { Check, ListPlus, Loader2, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { useGenerateTasks } from "@/hooks/use-ai";
import { useCreateTask } from "@/hooks/use-tasks";
import { useProjects } from "@/hooks/use-projects";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";
import type { TaskSuggestion } from "@/types/ai";

/**
 * Generates suggested tasks from a document (or text) and lets the user approve
 * each one into a real task. Nothing is created until the user clicks "Add" —
 * approval is required before write, per the spec.
 */
export function AISuggestionCard({
  documentId,
  text,
  defaultProjectId,
}: {
  documentId?: string;
  text?: string;
  defaultProjectId?: string | null;
}) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const generate = useGenerateTasks();
  const createTask = useCreateTask();
  const { data: projectsData } = useProjects({
    workspace: activeWorkspaceId ?? undefined,
  });

  const [suggestions, setSuggestions] = React.useState<TaskSuggestion[] | null>(null);
  const [projectId, setProjectId] = React.useState<string>(defaultProjectId ?? "");
  const [addingIndex, setAddingIndex] = React.useState<number | null>(null);

  const projects = projectsData?.results ?? [];

  async function handleGenerate() {
    if (!activeWorkspaceId) {
      toast.error("Select a workspace first.");
      return;
    }
    try {
      const res = await generate.mutateAsync({
        workspace: activeWorkspaceId,
        document: documentId,
        text,
      });
      setSuggestions(res.suggestions);
      if (!res.suggestions.length) toast.info("No action items found.");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  async function handleAdd(index: number, s: TaskSuggestion) {
    if (!projectId) {
      toast.error("Choose a project for the new task.");
      return;
    }
    setAddingIndex(index);
    try {
      await createTask.mutateAsync({
        project: projectId,
        title: s.title,
        description: s.description,
        priority: s.priority,
        due_date: s.due_date,
      });
      toast.success("Task created");
      setSuggestions((prev) => prev?.filter((_, i) => i !== index) ?? null);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setAddingIndex(null);
    }
  }

  function dismiss(index: number) {
    setSuggestions((prev) => prev?.filter((_, i) => i !== index) ?? null);
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <ListPlus className="size-4 text-muted-foreground" />
            Suggested tasks
          </CardTitle>
          <CardDescription>
            Extract action items and approve the ones you want to create.
          </CardDescription>
        </div>
        <Button size="sm" onClick={handleGenerate} disabled={generate.isPending}>
          {generate.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Sparkles className="size-4" />
              Generate
            </>
          )}
        </Button>
      </CardHeader>

      <CardContent className="space-y-3">
        {suggestions === null ? (
          <p className="text-sm text-muted-foreground">
            No suggestions yet — generate to extract tasks from this content.
          </p>
        ) : suggestions.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No action items were found.
          </p>
        ) : (
          <>
            <div className="max-w-xs">
              <Select value={projectId} onValueChange={setProjectId}>
                <SelectTrigger>
                  <SelectValue placeholder="Create tasks in project…" />
                </SelectTrigger>
                <SelectContent>
                  {projects.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <ul className="space-y-2">
              {suggestions.map((s, i) => (
                <li
                  key={`${s.title}-${i}`}
                  className="flex items-start justify-between gap-3 rounded-lg border p-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{s.title}</span>
                      <PriorityBadge priority={s.priority} />
                      {s.due_date && (
                        <span className="text-xs text-muted-foreground">
                          due {formatDate(s.due_date)}
                        </span>
                      )}
                    </div>
                    {s.description && (
                      <p className="text-sm text-muted-foreground">
                        {s.description}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      size="icon"
                      variant="outline"
                      className="size-8"
                      onClick={() => handleAdd(i, s)}
                      disabled={addingIndex === i}
                      aria-label="Add task"
                    >
                      {addingIndex === i ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Check className="size-4" />
                      )}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-8"
                      onClick={() => dismiss(i)}
                      aria-label="Dismiss suggestion"
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
