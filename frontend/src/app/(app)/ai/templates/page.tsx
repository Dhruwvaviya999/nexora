"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LibraryBig, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { PageHeader } from "@/components/shared/page-header";
import { SearchInput } from "@/components/shared/search-input";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  useCreatePromptTemplate,
  useDeletePromptTemplate,
  usePromptTemplates,
  useUpdatePromptTemplate,
} from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import {
  promptTemplateSchema,
  type PromptTemplateValues,
} from "@/lib/validations/ai";
import type { PromptTemplate } from "@/types/ai";

export default function PromptLibraryPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const [search, setSearch] = React.useState("");
  const { data, isLoading } = usePromptTemplates(activeWorkspaceId ?? undefined, {
    search: search || undefined,
  });

  const createTemplate = useCreatePromptTemplate();
  const updateTemplate = useUpdatePromptTemplate();
  const deleteTemplate = useDeletePromptTemplate();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<PromptTemplate | null>(null);
  const [pendingDelete, setPendingDelete] = React.useState<string | null>(null);

  const form = useForm<PromptTemplateValues>({
    resolver: zodResolver(promptTemplateSchema),
    defaultValues: {
      name: "",
      description: "",
      category: "general",
      template: "",
      is_shared: true,
    },
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const templates = data?.results ?? [];

  function openCreate() {
    setEditing(null);
    form.reset({
      name: "",
      description: "",
      category: "general",
      template: "",
      is_shared: true,
    });
    setDialogOpen(true);
  }

  function openEdit(t: PromptTemplate) {
    setEditing(t);
    form.reset({
      name: t.name,
      description: t.description,
      category: t.category,
      template: t.template,
      is_shared: t.is_shared,
    });
    setDialogOpen(true);
  }

  async function onSubmit(values: PromptTemplateValues) {
    try {
      if (editing) {
        await updateTemplate.mutateAsync({ id: editing.id, payload: values });
        toast.success("Template updated");
      } else {
        await createTemplate.mutateAsync({
          workspace: activeWorkspaceId as string,
          ...values,
        });
        toast.success("Template created");
      }
      setDialogOpen(false);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    try {
      await deleteTemplate.mutateAsync(pendingDelete);
      toast.success("Template deleted");
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prompt library"
        description="Reusable prompts your team can drop into the assistant."
      >
        <Button onClick={openCreate}>
          <Plus className="size-4" />
          New template
        </Button>
      </PageHeader>

      <SearchInput
        value={search}
        onSearch={setSearch}
        placeholder="Search templates…"
        className="sm:max-w-xs"
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : templates.length === 0 ? (
        <EmptyState
          icon={LibraryBig}
          title="No templates yet"
          description="Create a prompt template to reuse across chats."
          action={<Button onClick={openCreate}>New template</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <Card key={t.id} className="flex flex-col">
              <CardHeader className="space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{t.name}</CardTitle>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      onClick={() => openEdit(t)}
                      aria-label="Edit template"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-7 text-muted-foreground hover:text-destructive"
                      onClick={() => setPendingDelete(t.id)}
                      aria-label="Delete template"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="secondary" className="border-0">
                    {t.category || "general"}
                  </Badge>
                  {!t.is_shared && <Badge variant="outline">Private</Badge>}
                </div>
              </CardHeader>
              <CardContent className="flex-1">
                {t.description && (
                  <p className="mb-2 text-sm text-muted-foreground">
                    {t.description}
                  </p>
                )}
                <p className="line-clamp-4 whitespace-pre-wrap rounded-md bg-muted p-2 text-xs text-muted-foreground">
                  {t.template}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit template" : "New template"}
            </DialogTitle>
            <DialogDescription>
              Save a reusable prompt for your workspace.
            </DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Weekly status update" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category</FormLabel>
                      <FormControl>
                        <Input placeholder="general" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="is_shared"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-md border px-3 py-2">
                      <FormLabel className="m-0">Shared</FormLabel>
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input placeholder="What is this prompt for?" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="template"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prompt</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={5}
                        placeholder="Summarize the key updates for {{project}} this week…"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="submit" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting
                    ? "Saving…"
                    : editing
                      ? "Save changes"
                      : "Create template"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title="Delete template?"
        description="This permanently removes the prompt template."
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  );
}
