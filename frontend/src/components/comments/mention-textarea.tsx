"use client";

import * as React from "react";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { initialsOf } from "@/lib/initials";
import type { WorkspaceMember } from "@/types/workspace";

interface MentionTextareaProps {
  value: string;
  onChange: (value: string) => void;
  members: WorkspaceMember[];
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

// The active "@query" sitting just before the caret (word start or whitespace).
const ACTIVE_MENTION_RE = /(^|\s)@([\w.\-]*)$/;

/**
 * Textarea with @-mention autocomplete. Inserts `@[Name](id)` tokens that the
 * backend parses and `CommentContent` renders. Suggestions are drawn from the
 * workspace members.
 */
export function MentionTextarea({
  value,
  onChange,
  members,
  placeholder,
  disabled,
  autoFocus,
}: MentionTextareaProps) {
  const ref = React.useRef<HTMLTextAreaElement>(null);
  const [query, setQuery] = React.useState<string | null>(null);

  const suggestions =
    query !== null
      ? members
          .filter((m) => {
            const haystack = `${m.user.name} ${m.user.email}`.toLowerCase();
            return haystack.includes(query.toLowerCase());
          })
          .slice(0, 6)
      : [];

  function syncQuery(el: HTMLTextAreaElement) {
    const caret = el.selectionStart ?? el.value.length;
    const before = el.value.slice(0, caret);
    const match = before.match(ACTIVE_MENTION_RE);
    setQuery(match ? match[2] : null);
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    onChange(e.target.value);
    syncQuery(e.target);
  }

  function insertMention(member: WorkspaceMember) {
    const el = ref.current;
    if (!el) return;
    const caret = el.selectionStart ?? value.length;
    const before = value.slice(0, caret);
    const after = value.slice(caret);

    const match = before.match(ACTIVE_MENTION_RE);
    if (!match) return;
    const lead = match[1]; // preserved leading space (or "")
    const label = member.user.name || member.user.email;
    const token = `${lead}@[${label}](${member.user.id}) `;
    const newBefore = before.slice(0, before.length - match[0].length) + token;

    onChange(newBefore + after);
    setQuery(null);

    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(newBefore.length, newBefore.length);
    });
  }

  return (
    <div className="relative">
      <Textarea
        ref={ref}
        value={value}
        onChange={handleChange}
        onKeyUp={(e) => syncQuery(e.currentTarget)}
        onClick={(e) => syncQuery(e.currentTarget)}
        onBlur={() => setQuery(null)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        rows={3}
        className="resize-none"
      />
      {suggestions.length > 0 && (
        <div className="absolute z-20 mt-1 w-64 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md">
          {suggestions.map((m) => (
            <button
              key={m.id}
              type="button"
              // onMouseDown (not click) so it fires before the textarea blur.
              onMouseDown={(e) => {
                e.preventDefault();
                insertMention(m);
              }}
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-accent"
            >
              <Avatar className="size-6">
                <AvatarImage src={m.user.avatar || undefined} />
                <AvatarFallback className="text-[10px]">
                  {initialsOf(m.user.name, m.user.email)}
                </AvatarFallback>
              </Avatar>
              <span className="truncate">{m.user.name || m.user.email}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
