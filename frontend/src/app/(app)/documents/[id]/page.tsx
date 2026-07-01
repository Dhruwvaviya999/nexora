"use client";

import { useParams } from "next/navigation";
import { Download, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { CollaborationTabs } from "@/components/comments/collaboration-tabs";
import { AISummaryCard } from "@/components/ai/ai-summary-card";
import { AISuggestionCard } from "@/components/ai/ai-suggestion-card";
import { EmbeddingStatusBadge } from "@/components/ai/embedding-status-badge";
import { useDocument, useReindexDocument } from "@/hooks/use-documents";
import { getErrorMessage } from "@/lib/api/errors";
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
  const reindex = useReindexDocument();

  async function handleReindex() {
    try {
      const res = await reindex.mutateAsync(id);
      if (res.status === "completed") {
        toast.success(`Indexed (${res.chunk_count} chunks)`);
      } else if (res.status === "failed") {
        toast.error(res.error || "Indexing failed");
      } else {
        toast.info("Indexing started");
      }
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

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
          <Button asChild variant="outline">
            <a href={doc.file_url} target="_blank" rel="noreferrer" download>
              <Download className="size-4" />
              Download
            </a>
          </Button>
        )}
      </PageHeader>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">File details</CardTitle>
          <div className="flex items-center gap-2">
            <EmbeddingStatusBadge
              status={doc.embedding_status}
              chunkCount={doc.chunk_count}
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReindex}
              disabled={reindex.isPending}
            >
              <RefreshCw
                className={reindex.isPending ? "size-4 animate-spin" : "size-4"}
              />
              Re-index
            </Button>
          </div>
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

      {/* AI Document Insights */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">
          AI insights
        </h2>
        <AISummaryCard
          targetType="document"
          targetId={doc.id}
          title="Document summary"
          description="An AI summary of this document's contents."
        />
        <AISuggestionCard documentId={doc.id} defaultProjectId={doc.project} />
      </div>

      <CollaborationTabs targetType="document" targetId={doc.id} />
    </div>
  );
}
