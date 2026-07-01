"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { AISource } from "@/types/ai";

function scoreTint(score: number): string {
  if (score >= 0.6) return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400";
  if (score >= 0.4) return "bg-amber-500/15 text-amber-600 dark:text-amber-400";
  return "bg-muted text-muted-foreground";
}

/** Ranked semantic-search results with similarity scores and source links. */
export function SearchResults({ results }: { results: AISource[] }) {
  return (
    <div className="space-y-3">
      {results.map((r, i) => (
        <Card key={r.chunk_id} className="overflow-hidden">
          <CardContent className="space-y-2 p-4">
            <div className="flex items-start justify-between gap-3">
              <Link
                href={ROUTES.document(r.document_id)}
                className="flex min-w-0 items-center gap-2 font-medium hover:underline"
              >
                <FileText className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{r.title}</span>
              </Link>
              <Badge
                variant="secondary"
                className={cn("shrink-0 border-0 tabular-nums", scoreTint(r.score))}
              >
                {Math.round(r.score * 100)}% match
              </Badge>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {r.content}
            </p>
            <p className="text-xs text-muted-foreground">
              Result {i + 1} · chunk #{r.chunk_index}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
