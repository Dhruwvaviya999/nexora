import { Bot, User } from "lucide-react";

import { cn } from "@/lib/utils";
import { InlineSources } from "@/components/ai/sources-panel";
import { ConfidenceBadge } from "@/components/ai/confidence-badge";
import { TypingIndicator } from "@/components/ai/typing-indicator";
import type { AIMessage, AISource, Confidence } from "@/types/ai";

/**
 * A single chat turn. The assistant side renders sources + an optional
 * confidence badge; `pending` swaps the body for a typing indicator so the
 * UI is streaming-ready (text can later be filled token-by-token).
 */
export function MessageBubble({
  message,
  confidence,
  pending = false,
}: {
  message: Pick<AIMessage, "role" | "content"> & { sources?: AISource[] };
  confidence?: Confidence;
  pending?: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>

      <div className={cn("min-w-0 max-w-[85%] space-y-1.5", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm bg-muted"
          )}
        >
          {pending ? (
            <TypingIndicator className="py-1" />
          ) : (
            <p className="whitespace-pre-wrap break-words leading-relaxed">
              {message.content}
            </p>
          )}
        </div>

        {!isUser && !pending && (
          <>
            {confidence && <ConfidenceBadge confidence={confidence} />}
            <InlineSources sources={message.sources ?? []} />
          </>
        )}
      </div>
    </div>
  );
}
