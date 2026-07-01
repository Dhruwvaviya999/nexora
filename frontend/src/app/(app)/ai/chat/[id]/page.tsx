"use client";

import { useParams } from "next/navigation";

import { ChatWindow } from "@/components/ai/chat-window";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { useWorkspaceContext } from "@/providers/workspace-provider";

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const { activeWorkspaceId, isLoading } = useWorkspaceContext();
  if (!isLoading && !activeWorkspaceId) return <NoWorkspace />;
  return <ChatWindow conversationId={id} />;
}
