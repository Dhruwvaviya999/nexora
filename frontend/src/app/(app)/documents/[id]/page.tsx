"use client";

import * as React from "react";
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
import { downloadFile } from "@/lib/api/download";
import { getErrorMessage } from "@/lib/api/errors";
import { API_ROUTES } from "@/lib/constants";
import { formatBytes, formatDateTime } from "@/lib/format";

import { PageContainer } from "@/components/layout/page-container";
import { ErrorState } from "@/components/shared/error-state";
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
  const { data: doc, isLoading, isError, error, refetch } = useDocument(id);
  const reindex = useReindexDocument();
  const [downloading, setDownloading] = React.useState(false);

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

  // A failed fetch used to be indistinguishable from a slow one and
  // spun forever; surface the real error instead.
  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (isLoading || !doc) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <PageContainer size="sm" className="space-y-6">
      <PageHeader title={doc.title} description={doc.description || "No description"}>
        {doc.file_url && (
          // Not a plain <a href>: the file is served by an authenticated,
          // workspace-scoped endpoint, so it has to be fetched with the bearer
          // token and handed to the browser as a blob.
          <Button
            variant="outline"
            disabled={downloading}
            onClick={async () => {
              setDownloading(true);
              try {
                await downloadFile(
                  API_ROUTES.documents.download(doc.id),
                  doc.title
                );
              } catch (e) {
                toast.error(getErrorMessage(e));
              } finally {
                setDownloading(false);
              }
            }}
          >
            <Download className="size-4" />
            {downloading ? "Downloading…" : "Download"}
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
    </PageContainer>
  );
}
