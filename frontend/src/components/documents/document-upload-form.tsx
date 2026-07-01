"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUpload } from "@/components/shared/file-upload";
import { useProjects } from "@/hooks/use-projects";
import { documentSchema, type DocumentValues } from "@/lib/validations/document";

const NO_PROJECT = "none";

export function DocumentUploadForm({
  workspaceId,
  onSubmit,
}: {
  workspaceId: string;
  onSubmit: (values: DocumentValues) => Promise<void> | void;
}) {
  const { data: projectsData } = useProjects({ workspace: workspaceId });
  const projects = projectsData?.results ?? [];

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<DocumentValues>({
    resolver: zodResolver(documentSchema),
    defaultValues: { title: "", description: "", project: "" },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="space-y-2">
        <Label>File</Label>
        <Controller
          control={control}
          name="file"
          render={({ field }) => (
            <FileUpload
              value={field.value ?? null}
              onChange={(f) => field.onChange(f)}
            />
          )}
        />
        {errors.file && (
          <p className="text-sm text-destructive">{errors.file.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input id="title" placeholder="Defaults to the filename" {...register("title")} />
      </div>

      <div className="space-y-2">
        <Label>Project (optional)</Label>
        <Controller
          control={control}
          name="project"
          render={({ field }) => (
            <Select
              value={field.value || NO_PROJECT}
              onValueChange={(v) => field.onChange(v === NO_PROJECT ? "" : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="No project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_PROJECT}>No project</SelectItem>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" rows={3} {...register("description")} />
      </div>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Uploading…" : "Upload document"}
      </Button>
    </form>
  );
}
