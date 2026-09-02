"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DatePicker } from "@/components/shared/date-picker";
import { useProjects } from "@/hooks/use-projects";
import { useWorkspaceMembers } from "@/hooks/use-workspaces";
import { taskSchema, type TaskValues } from "@/lib/validations/task";
import { TASK_PRIORITIES, TASK_STATUSES } from "@/lib/constants";

const UNASSIGNED = "unassigned";

function parseLabels(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Comma-separated labels editor. Keeps the raw text locally so a trailing comma
 * or space survives while typing; the form only ever sees the parsed array.
 */
function LabelsInput({
  value,
  onChange,
}: {
  value?: string[] | null;
  onChange: (labels: string[]) => void;
}) {
  const labels = value ?? [];
  const key = labels.join(",");
  const [draft, setDraft] = React.useState(() => labels.join(", "));
  const [syncedKey, setSyncedKey] = React.useState(key);

  // Adjust during render (not in an effect) when the form value changed from the
  // outside — a reset or defaults arriving. Edits made here already match the
  // draft, so the raw text is left alone.
  if (key !== syncedKey) {
    setSyncedKey(key);
    if (parseLabels(draft).join(",") !== key) setDraft(labels.join(", "));
  }

  return (
    <Input
      placeholder="design, frontend"
      value={draft}
      onChange={(e) => {
        setDraft(e.target.value);
        onChange(parseLabels(e.target.value));
      }}
      onBlur={() => setDraft(parseLabels(draft).join(", "))}
    />
  );
}

export function TaskForm({
  workspaceId,
  defaultValues,
  submitLabel = "Save",
  onSubmit,
}: {
  workspaceId: string;
  defaultValues?: Partial<TaskValues>;
  submitLabel?: string;
  onSubmit: (values: TaskValues) => Promise<void> | void;
}) {
  const { data: projectsData } = useProjects({ workspace: workspaceId });
  const { data: members } = useWorkspaceMembers(workspaceId);
  const projects = projectsData?.results ?? [];

  const form = useForm<TaskValues>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      project: defaultValues?.project ?? "",
      title: defaultValues?.title ?? "",
      description: defaultValues?.description ?? "",
      status: defaultValues?.status ?? "todo",
      priority: defaultValues?.priority ?? "medium",
      assignee_id: defaultValues?.assignee_id ?? "",
      due_date: defaultValues?.due_date ?? "",
      start_date: defaultValues?.start_date ?? "",
      estimated_hours: defaultValues?.estimated_hours ?? "",
      labels: defaultValues?.labels ?? [],
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Title</FormLabel>
              <FormControl>
                <Input placeholder="Design the homepage" maxLength={255} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="project"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Project</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a project" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="assignee_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Assignee</FormLabel>
                <Select
                  value={field.value || UNASSIGNED}
                  onValueChange={(v) =>
                    field.onChange(v === UNASSIGNED ? "" : v)
                  }
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Unassigned" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                    {members?.map((m) => (
                      <SelectItem key={m.user.id} value={m.user.id}>
                        {m.user.name || m.user.email}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Status</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {TASK_STATUSES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="priority"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Priority</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {TASK_PRIORITIES.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="due_date"
            render={({ field }) => (
              <FormItem className="flex flex-col">
                <FormLabel>Due date</FormLabel>
                <DatePicker value={field.value} onChange={field.onChange} />
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="estimated_hours"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Estimated hours</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="0.5"
                    min="0"
                    max="9999.99"
                    placeholder="e.g. 4"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="labels"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Labels</FormLabel>
              <FormControl>
                <LabelsInput
                  value={field.value}
                  onChange={field.onChange}
                />
              </FormControl>
              <FormDescription>Comma-separated.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea rows={4} maxLength={5000} placeholder="Details…" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : submitLabel}
        </Button>
      </form>
    </Form>
  );
}
