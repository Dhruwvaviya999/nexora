"use client";

import { useParams } from "next/navigation";
import { Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { CollaborationTabs } from "@/components/comments/collaboration-tabs";
import { useDocument } from "@/hooks/use-documents";
import { formatBytes, formatDateTime } from "@/lib/format";

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="text-sm">{value}</div>
    </div>
  );
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: doc, isLoading } = useDocument(id);

  if (isLoading || !doc) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageHeader title={doc.title} description={doc.description || "No description"}>
        {doc.file_url && (
          <Button asChild>
            <a href={doc.file_url} target="_blank" rel="noreferrer" download>
              <Download className="size-4" />
              Download
            </a>
          </Button>
        )}
      </PageHeader>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">File details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 sm:grid-cols-2">
          <Detail label="Type" value={doc.file_type || "—"} />
          <Detail label="Size" value={formatBytes(doc.file_size)} />
          <Detail
            label="Uploaded by"
            value={doc.uploaded_by?.name || doc.uploaded_by?.email || "—"}
          />
          <Detail label="Uploaded" value={formatDateTime(doc.created_at)} />
        </CardContent>
      </Card>

      <CollaborationTabs targetType="document" targetId={doc.id} />
    </div>
  );
}
