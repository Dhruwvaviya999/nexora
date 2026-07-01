"use client";

import * as React from "react";
import { Clock, Loader2, Search as SearchIcon, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { SearchResults } from "@/components/ai/search-results";
import { WorkspaceContextBadge } from "@/components/ai/workspace-context-badge";
import { useSearchHistory, useSemanticSearch } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import type { SearchResponse } from "@/types/ai";

const SUGGESTED = [
  "What is our leave policy?",
  "Onboarding checklist for new hires",
  "Security and data handling guidelines",
  "Quarterly goals and OKRs",
];

const LIMITS = [5, 10, 20];

export default function AISearchPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const search = useSemanticSearch();
  const { data: history } = useSearchHistory(activeWorkspaceId ?? undefined);

  const [query, setQuery] = React.useState("");
  const [limit, setLimit] = React.useState(10);
  const [result, setResult] = React.useState<SearchResponse | null>(null);

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  async function run(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 2 || !activeWorkspaceId) return;
    setQuery(trimmed);
    try {
      const res = await search.mutateAsync({
        workspace: activeWorkspaceId,
        query: trimmed,
        limit,
      });
      setResult(res);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  const recent = history?.results ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Search"
        description="Find answers by meaning, not just keywords."
      >
        <WorkspaceContextBadge />
      </PageHeader>

      {/* Query bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(query);
        }}
        className="flex flex-col gap-2 sm:flex-row"
      >
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question, e.g. “What is our refund policy?”"
            className="pl-9"
          />
        </div>
        <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
          <SelectTrigger className="w-full sm:w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LIMITS.map((n) => (
              <SelectItem key={n} value={String(n)}>
                Top {n} results
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button type="submit" disabled={search.isPending || query.trim().length < 2}>
          {search.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <SearchIcon className="size-4" />
          )}
          Search
        </Button>
      </form>

      {/* Results / states */}
      {search.isPending ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : result ? (
        result.results.length ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>
                {result.count} result{result.count === 1 ? "" : "s"} for{" "}
                <span className="font-medium text-foreground">
                  “{result.query}”
                </span>
              </span>
              <Badge variant="secondary" className="border-0">
                best match {Math.round(result.top_score * 100)}%
              </Badge>
            </div>
            <SearchResults results={result.results} />
          </div>
        ) : (
          <EmptyState
            icon={SearchIcon}
            title="No matching content"
            description={`Nothing in this workspace closely matches “${result.query}”. Try rephrasing, or upload more documents.`}
          />
        )
      ) : (
        <div className="space-y-8 py-6">
          <div className="space-y-3">
            <p className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              <Sparkles className="size-4" />
              Suggested searches
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED.map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  size="sm"
                  onClick={() => run(s)}
                  className="h-auto whitespace-normal py-1.5 text-left"
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>

          {recent.length > 0 && (
            <div className="space-y-3">
              <p className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
                <Clock className="size-4" />
                Recent queries
              </p>
              <div className="flex flex-wrap gap-2">
                {recent.slice(0, 12).map((h) => (
                  <Button
                    key={h.id}
                    variant="ghost"
                    size="sm"
                    onClick={() => run(h.query)}
                    className="h-auto border py-1.5"
                  >
                    {h.query}
                    <Badge variant="secondary" className="ml-1 border-0">
                      {h.results_count}
                    </Badge>
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
