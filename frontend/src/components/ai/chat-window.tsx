"use client";

import * as React from "react";
import { CornerDownLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble } from "@/components/ai/message-bubble";
import { SuggestedPrompts } from "@/components/ai/suggested-prompts";
import { WorkspaceContextBadge } from "@/components/ai/workspace-context-badge";
import { useConversation, useSendChat } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { AISource, Confidence } from "@/types/ai";

interface LocalMessage {
  role: "user" | "assistant";
  content: string;
  sources?: AISource[];
  confidence?: Confidence;
}

/**
 * ChatGPT-style conversation surface. Works for a brand-new chat (no id) or an
 * existing conversation. Messages are kept locally for an instant, optimistic
 * feel; the architecture is streaming-ready (the assistant bubble shows a typing
 * indicator while pending and could be filled token-by-token later).
 */
export function ChatWindow({
  conversationId,
}: {
  conversationId?: string;
}) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const sendChat = useSendChat();
  const { data: conversation, isLoading } = useConversation(conversationId);

  const [convoId, setConvoId] = React.useState<string | undefined>(conversationId);
  const [messages, setMessages] = React.useState<LocalMessage[]>([]);
  const [input, setInput] = React.useState("");
  const seededRef = React.useRef<string | undefined>(undefined);
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const pending = sendChat.isPending;

  // Seed local messages from the server once per conversation.
  React.useEffect(() => {
    if (conversation && seededRef.current !== conversation.id) {
      setMessages(
        conversation.messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          sources: m.sources,
        }))
      );
      seededRef.current = conversation.id;
      setConvoId(conversation.id);
    }
  }, [conversation]);

  // Keep the latest message in view.
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, pending]);

  const send = React.useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;
      if (!activeWorkspaceId) {
        toast.error("Select a workspace first.");
        return;
      }
      setInput("");
      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      try {
        const res = await sendChat.mutateAsync({
          workspace: activeWorkspaceId,
          conversation: convoId,
          message: trimmed,
        });
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: res.message.content,
            sources: res.message.sources,
            confidence: res.confidence,
          },
        ]);
        if (!convoId) {
          // New conversation: adopt its id and reflect it in the URL without a
          // remount so local messages are preserved.
          setConvoId(res.conversation);
          seededRef.current = res.conversation;
          window.history.replaceState(null, "", ROUTES.aiConversation(res.conversation));
        }
      } catch (e) {
        toast.error(getErrorMessage(e));
      }
    },
    [activeWorkspaceId, convoId, pending, sendChat]
  );

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const isEmpty = messages.length === 0 && !pending;
  const loadingHistory = !!conversationId && isLoading && messages.length === 0;

  return (
    <div className="flex h-[calc(100svh-9rem)] flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {loadingHistory ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6 px-4">
            <div className="space-y-1 text-center">
              <h2 className="text-xl font-semibold">Ask your workspace anything</h2>
              <p className="text-sm text-muted-foreground">
                Answers are grounded in this workspace&apos;s documents, projects
                and tasks.
              </p>
            </div>
            <SuggestedPrompts onSelect={send} />
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 px-1 py-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} message={m} confidence={m.confidence} />
            ))}
            {pending && (
              <MessageBubble
                message={{ role: "assistant", content: "", sources: [] }}
                pending
              />
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="mx-auto w-full max-w-3xl pt-3">
        <div className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Message the assistant…  (Enter to send, Shift+Enter for newline)"
            className="max-h-40 min-h-10 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          <Button
            size="icon"
            className="size-9 shrink-0"
            disabled={pending || !input.trim()}
            onClick={() => send(input)}
            aria-label="Send message"
          >
            {pending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <CornerDownLeft className="size-4" />
            )}
          </Button>
        </div>
        <div className="mt-2 flex justify-center">
          <WorkspaceContextBadge />
        </div>
      </div>
    </div>
  );
}
