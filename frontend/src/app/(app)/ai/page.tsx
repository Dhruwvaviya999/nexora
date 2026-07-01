"use client";

import Link from "next/link";
import {
  Bot,
  LibraryBig,
  MessagesSquare,
  MessageSquare,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { AISummaryCard } from "@/components/ai/ai-summary-card";
import { WorkspaceContextBadge } from "@/components/ai/workspace-context-badge";
import { useConversations, useSearchHistory } from "@/hooks/use-ai";
import { useDocuments } from "@/hooks/use-documents";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/format";

const QUICK_ACTIONS = [
  { title: "Start a chat", href: ROUTES.aiChat, icon: MessagesSquare, desc: "Ask about your workspace" },
  { title: "Semantic search", href: ROUTES.aiSearch, icon: Bot, desc: "Find answers by meaning" },
  { title: "Prompt library", href: ROUTES.aiTemplates, icon: LibraryBig, desc: "Reusable prompts" },
  { title: "AI settings", href: ROUTES.aiSettings, icon: Settings, desc: "Provider & models" },
];

export default function AIDashboardPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const ws = activeWorkspaceId ?? undefined;

  const conversations = useConversations(ws);
  const searches = useSearchHistory(ws);
  const documents = useDocuments({ workspace: ws });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const recentConversations = conversations.data?.results?.slice(0, 5) ?? [];
  const loadingStats =
    conversations.isLoading || searches.isLoading || documents.isLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Assistant"
        description="Your workspace's knowledge, on demand."
      >
        <WorkspaceContextBadge />
      </PageHeader>

      {/* Stats */}
      {loadingStats ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Conversations"
            value={conversations.data?.count ?? 0}
            icon={MessagesSquare}
          />
          <StatCard
            label="Searches"
            value={searches.data?.count ?? 0}
            icon={Search}
          />
          <StatCard
            label="Documents"
            value={documents.data?.count ?? 0}
            icon={LibraryBig}
            hint="Available for retrieval"
          />
        </div>
      )}

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_ACTIONS.map((a) => (
          <Link key={a.href} href={a.href}>
            <Card className="h-full transition-colors hover:border-primary/40 hover:bg-accent/40">
              <CardContent className="flex items-start gap-3 p-5">
                <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
                  <a.icon className="size-5" />
                </div>
                <div className="space-y-0.5">
                  <p className="font-medium">{a.title}</p>
                  <p className="text-sm text-muted-foreground">{a.desc}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Weekly AI summary */}
        <AISummaryCard
          targetType="activity"
          period="week"
          title="This week, summarized"
          description="An AI digest of recent workspace activity."
        />

        {/* Recent conversations */}
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="size-4 text-muted-foreground" />
              Recent conversations
            </CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link href={ROUTES.aiConversations}>View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {conversations.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-9 w-full" />
                ))}
              </div>
            ) : recentConversations.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No conversations yet"
                description="Start a chat to see it here."
                action={
                  <Button asChild size="sm">
                    <Link href={ROUTES.aiChat}>New chat</Link>
                  </Button>
                }
              />
            ) : (
              <ul className="divide-y">
                {recentConversations.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={ROUTES.aiConversation(c.id)}
                      className="flex items-center justify-between gap-2 py-2.5 hover:text-primary"
                    >
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">
                        {c.title || "Untitled chat"}
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatRelativeTime(c.updated_at)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
