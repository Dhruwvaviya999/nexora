"use client";

import * as React from "react";
import Link from "next/link";
import { MessagesSquare, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useConversations, useDeleteConversation } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/format";

export default function ConversationsPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const { data, isLoading } = useConversations(activeWorkspaceId ?? undefined);
  const del = useDeleteConversation();
  const [pendingDelete, setPendingDelete] = React.useState<string | null>(null);

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const conversations = data?.results ?? [];

  async function confirmDelete() {
    if (!pendingDelete) return;
    try {
      await del.mutateAsync(pendingDelete);
      toast.success("Conversation deleted");
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conversation history"
        description="Your past chats with the assistant."
      >
        <Button asChild>
          <Link href={ROUTES.aiChat}>
            <Plus className="size-4" />
            New chat
          </Link>
        </Button>
      </PageHeader>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : conversations.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="No conversations yet"
          description="Start chatting with your workspace assistant."
          action={
            <Button asChild>
              <Link href={ROUTES.aiChat}>Start a chat</Link>
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="divide-y p-0">
            {conversations.map((c) => (
              <div
                key={c.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-accent/40"
              >
                <MessagesSquare className="size-4 shrink-0 text-muted-foreground" />
                <Link
                  href={ROUTES.aiConversation(c.id)}
                  className="min-w-0 flex-1"
                >
                  <p className="truncate font-medium">
                    {c.title || "Untitled chat"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {c.message_count} message{c.message_count === 1 ? "" : "s"} ·{" "}
                    {formatRelativeTime(c.updated_at)}
                  </p>
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => setPendingDelete(c.id)}
                  aria-label="Delete conversation"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title="Delete conversation?"
        description="This permanently removes the conversation and its messages."
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  );
}
