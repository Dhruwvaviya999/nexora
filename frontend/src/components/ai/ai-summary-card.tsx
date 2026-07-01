"use client";

import * as React from "react";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSummarize } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import type { SummaryPeriod, SummaryTarget } from "@/types/ai";

/** On-demand AI summary for a project, task, document, or workspace activity. */
export function AISummaryCard({
  targetType,
  targetId,
  period,
  title = "AI summary",
  description,
}: {
  targetType: SummaryTarget;
  targetId?: string;
  period?: SummaryPeriod;
  title?: string;
  description?: string;
}) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const summarize = useSummarize();
  const [summary, setSummary] = React.useState<string | null>(null);

  async function handleGenerate() {
    if (!activeWorkspaceId) {
      toast.error("Select a workspace first.");
      return;
    }
    try {
      const res = await summarize.mutateAsync({
        workspace: activeWorkspaceId,
        target_type: targetType,
        target_id: targetId,
        period,
      });
      setSummary(res.summary);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="size-4 text-muted-foreground" />
            {title}
          </CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        <Button
          size="sm"
          variant={summary ? "outline" : "default"}
          onClick={handleGenerate}
          disabled={summarize.isPending}
        >
          {summarize.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Generating…
            </>
          ) : summary ? (
            "Regenerate"
          ) : (
            "Generate"
          )}
        </Button>
      </CardHeader>
      <CardContent>
        {summarize.isPending && !summary ? (
          <p className="text-sm text-muted-foreground">
            Reading workspace data and writing a summary…
          </p>
        ) : summary ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {summary}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Generate an AI summary grounded in this workspace&apos;s data.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
