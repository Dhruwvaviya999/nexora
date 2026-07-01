"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DocumentUploadForm } from "@/components/documents/document-upload-form";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useUploadDocument } from "@/hooks/use-documents";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { DocumentValues } from "@/lib/validations/document";

export default function NewDocumentPage() {
  const router = useRouter();
  const { activeWorkspaceId } = useWorkspaceContext();
  const uploadDocument = useUploadDocument();

  if (!activeWorkspaceId) return <NoWorkspace />;

  async function handleSubmit(values: DocumentValues) {
    const form = new FormData();
    form.append("workspace", activeWorkspaceId as string);
    form.append("file", values.file);
    if (values.project) form.append("project", values.project);
    if (values.title) form.append("title", values.title);
    if (values.description) form.append("description", values.description);

    try {
      const doc = await uploadDocument.mutateAsync(form);
      toast.success("Document uploaded");
      router.replace(ROUTES.document(doc.id));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <PageHeader title="Upload document" description="Add a file to this workspace." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Document</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentUploadForm
            workspaceId={activeWorkspaceId}
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </div>
  );
}
