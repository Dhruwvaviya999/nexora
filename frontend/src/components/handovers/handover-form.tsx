"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
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
import { useAuth } from "@/providers/auth-provider";
import { useTasks } from "@/hooks/use-tasks";
import { useWorkspaceMembers } from "@/hooks/use-workspaces";
import { handoverSchema, type HandoverValues } from "@/lib/validations/handover";

// Work that is already finished (or dropped) can't be handed over.
const OPEN_STATUSES = ["todo", "in_progress", "review"];

export function HandoverForm({
  workspaceId,
  defaultValues,
  submitLabel = "Submit handover",
  onSubmit,
}: {
  workspaceId: string;
  defaultValues?: Partial<HandoverValues>;
  submitLabel?: string;
  onSubmit: (values: HandoverValues) => Promise<void> | void;
}) {
  const { user } = useAuth();
  const { data: tasksData } = useTasks({ workspace: workspaceId });
  const { data: members } = useWorkspaceMembers(workspaceId);

  const tasks = (tasksData?.results ?? []).filter((t) =>
    OPEN_STATUSES.includes(t.status)
  );
  const recipients = (members ?? []).filter((m) => m.user.id !== user?.id);

  const form = useForm<HandoverValues>({
    resolver: zodResolver(handoverSchema),
    defaultValues: {
      task: defaultValues?.task ?? "",
      to_user_id: defaultValues?.to_user_id ?? "",
      summary: defaultValues?.summary ?? "",
      pending_items: defaultValues?.pending_items ?? "",
      resources: defaultValues?.resources ?? "",
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="task"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Task</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a task" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {tasks.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormDescription>Only open tasks can be handed over.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="to_user_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Hand over to</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a teammate" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {recipients.map((m) => (
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
        </div>

        <FormField
          control={form.control}
          name="summary"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Work summary</FormLabel>
              <FormControl>
                <Textarea
                  rows={4}
                  placeholder="What has been done so far?"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="pending_items"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Pending items</FormLabel>
              <FormControl>
                <Textarea
                  rows={3}
                  placeholder="What still needs to happen?"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="resources"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Resources</FormLabel>
              <FormControl>
                <Textarea
                  rows={3}
                  placeholder="Links, documents, or context the recipient needs"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Never include passwords or secrets here — share those through
                your password manager.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Submitting…" : submitLabel}
        </Button>
      </form>
    </Form>
  );
}
