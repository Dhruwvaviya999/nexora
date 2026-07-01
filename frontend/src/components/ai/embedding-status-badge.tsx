import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DocumentItem } from "@/types/document";

type Status = DocumentItem["embedding_status"];

const CONFIG: Record<
  NonNullable<Status>,
  { label: string; className: string }
> = {
  pending: {
    label: "Indexing queued",
    className: "bg-muted text-muted-foreground",
  },
  processing: {
    label: "Indexing…",
    className: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  },
  completed: {
    label: "Indexed",
    className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  },
  failed: {
    label: "Indexing failed",
    className: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  },
};

/** Shows whether a document has been embedded for semantic search. */
export function EmbeddingStatusBadge({
  status,
  chunkCount,
}: {
  status: Status;
  chunkCount?: number;
}) {
  if (!status) {
    return (
      <Badge variant="secondary" className="border-0 bg-muted text-muted-foreground">
        Not indexed
      </Badge>
    );
  }
  const cfg = CONFIG[status];
  return (
    <Badge variant="secondary" className={cn("border-0", cfg.className)}>
      {cfg.label}
      {status === "completed" && chunkCount ? ` · ${chunkCount} chunks` : ""}
    </Badge>
  );
}
