"use client";

import { ChatWindow } from "@/components/ai/chat-window";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { useWorkspaceContext } from "@/providers/workspace-provider";

export default function NewChatPage() {
  const { activeWorkspaceId, isLoading } = useWorkspaceContext();
  if (!isLoading && !activeWorkspaceId) return <NoWorkspace />;
  return <ChatWindow />;
}
