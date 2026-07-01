"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { AISource } from "@/types/ai";

function scoreTint(score: number): string {
  if (score >= 0.6) return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400";
  if (score >= 0.4) return "bg-amber-500/15 text-amber-600 dark:text-amber-400";
  return "bg-muted text-muted-foreground";
}

/** Lists the document chunks an answer / search result was grounded in. */
export function SourcesPanel({
  sources,
  className,
  showHeading = true,
}: {
  sources: AISource[];
  className?: string;
  showHeading?: boolean;
}) {
  if (!sources?.length) return null;

  return (
    <div className={cn("space-y-2", className)}>
      {showHeading && (
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Sources ({sources.length})
        </p>
      )}
      <ul className="space-y-2">
        {sources.map((s, i) => (
          <li key={s.chunk_id} className="rounded-lg border bg-card p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <Link
                href={ROUTES.document(s.document_id)}
                className="flex min-w-0 items-center gap-1.5 font-medium hover:underline"
              >
                <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">
                  {i + 1}. {s.title}
                </span>
              </Link>
              <Badge
                variant="secondary"
                className={cn("shrink-0 border-0 tabular-nums", scoreTint(s.score))}
              >
                {Math.round(s.score * 100)}%
              </Badge>
            </div>
            <p className="mt-1.5 line-clamp-3 text-muted-foreground">{s.content}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Collapsible sources list shown beneath an assistant chat bubble. */
export function InlineSources({ sources }: { sources: AISource[] }) {
  const [open, setOpen] = React.useState(false);
  if (!sources?.length) return null;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronDown
          className={cn("size-3.5 transition-transform", open && "rotate-180")}
        />
        {open ? "Hide" : "Show"} sources ({sources.length})
      </button>
      {open && <SourcesPanel sources={sources} showHeading={false} className="mt-2" />}
    </div>
  );
}
