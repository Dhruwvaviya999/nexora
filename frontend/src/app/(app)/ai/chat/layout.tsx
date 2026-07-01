"use client";

import * as React from "react";
import { MessagesSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ConversationList } from "@/components/ai/conversation-list";

/**
 * Two-pane chat shell: a conversation list beside the active thread on desktop,
 * collapsing into a slide-over sheet on mobile.
 */
export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);

  return (
    <div className="flex gap-4">
      {/* Desktop conversation rail */}
      <aside className="hidden w-64 shrink-0 md:block">
        <ConversationList />
      </aside>

      <div className="min-w-0 flex-1">
        {/* Mobile conversation trigger */}
        <div className="mb-2 md:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm">
                <MessagesSquare className="size-4" />
                Conversations
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-4">
              <SheetHeader className="px-0">
                <SheetTitle>Conversations</SheetTitle>
              </SheetHeader>
              <ConversationList onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
        </div>

        {children}
      </div>
    </div>
  );
}
