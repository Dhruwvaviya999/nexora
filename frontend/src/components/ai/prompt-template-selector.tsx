"use client";

import { LibraryBig } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePromptTemplates } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";

/** Insert a saved prompt template into a chat/search input. */
export function PromptTemplateSelector({
  onSelect,
}: {
  onSelect: (template: string) => void;
}) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const { data } = usePromptTemplates(activeWorkspaceId ?? undefined);
  const templates = data?.results ?? [];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <LibraryBig className="size-4" />
          Templates
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel>Prompt library</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {templates.length === 0 ? (
          <DropdownMenuItem disabled>No templates yet</DropdownMenuItem>
        ) : (
          templates.map((t) => (
            <DropdownMenuItem
              key={t.id}
              onSelect={() => onSelect(t.template)}
              className="flex flex-col items-start gap-0.5"
            >
              <span className="font-medium">{t.name}</span>
              {t.description && (
                <span className="line-clamp-1 text-xs text-muted-foreground">
                  {t.description}
                </span>
              )}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
