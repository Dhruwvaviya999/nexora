"use client";

import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

export const DEFAULT_SUGGESTIONS = [
  "What tasks are overdue?",
  "Summarize what changed this week.",
  "Which projects are active right now?",
  "What is our leave policy?",
];

/** Clickable starter prompts shown on an empty chat / search page. */
export function SuggestedPrompts({
  prompts = DEFAULT_SUGGESTIONS,
  onSelect,
  title = "Try asking",
}: {
  prompts?: string[];
  onSelect: (prompt: string) => void;
  title?: string;
}) {
  if (!prompts.length) return null;
  return (
    <div className="space-y-3">
      <p className="flex items-center justify-center gap-1.5 text-sm text-muted-foreground">
        <Sparkles className="size-4" />
        {title}
      </p>
      <div className="mx-auto flex max-w-2xl flex-wrap justify-center gap-2">
        {prompts.map((p) => (
          <Button
            key={p}
            type="button"
            variant="outline"
            size="sm"
            className="h-auto whitespace-normal py-1.5 text-left"
            onClick={() => onSelect(p)}
          >
            {p}
          </Button>
        ))}
      </div>
    </div>
  );
}
