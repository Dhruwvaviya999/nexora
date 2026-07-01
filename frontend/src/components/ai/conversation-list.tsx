"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useConversations, useDeleteConversation } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Left-hand list of chat threads with new/delete controls. */
export function ConversationList({
  activeId,
  onNavigate,
}: {
  activeId?: string;
  onNavigate?: () => void;
}) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const { data, isLoading } = useConversations(activeWorkspaceId ?? undefined);
  const del = useDeleteConversation();
  const pathname = usePathname();

  const conversations = data?.results ?? [];

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await del.mutateAsync(id);
      toast.success("Conversation deleted");
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <Button asChild variant="outline" className="justify-start" onClick={onNavigate}>
        <Link href={ROUTES.aiChat}>
          <Plus className="size-4" />
          New chat
        </Link>
      </Button>

      <div className="flex-1 space-y-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-2 p-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            No conversations yet.
          </p>
        ) : (
          conversations.map((c) => {
            const active = activeId
              ? c.id === activeId
              : pathname === ROUTES.aiConversation(c.id);
            return (
              <Link
                key={c.id}
                href={ROUTES.aiConversation(c.id)}
                onClick={onNavigate}
                className={cn(
                  "group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent",
                  active && "bg-accent font-medium"
                )}
              >
                <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate">
                  {c.title || "Untitled chat"}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground group-hover:hidden">
                  {formatRelativeTime(c.updated_at)}
                </span>
                <button
                  type="button"
                  onClick={(e) => handleDelete(e, c.id)}
                  className="hidden shrink-0 text-muted-foreground hover:text-destructive group-hover:block"
                  aria-label="Delete conversation"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
