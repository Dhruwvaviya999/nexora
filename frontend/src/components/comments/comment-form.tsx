"use client";

import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { MentionTextarea } from "@/components/comments/mention-textarea";
import { getErrorMessage } from "@/lib/api/errors";
import type { WorkspaceMember } from "@/types/workspace";

interface CommentFormProps {
  members: WorkspaceMember[];
  onSubmit: (content: string) => Promise<unknown>;
  submitLabel?: string;
  placeholder?: string;
  initialValue?: string;
  autoFocus?: boolean;
  onCancel?: () => void;
}

export function CommentForm({
  members,
  onSubmit,
  submitLabel = "Comment",
  placeholder = "Write a comment… use @ to mention someone",
  initialValue = "",
  autoFocus,
  onCancel,
}: CommentFormProps) {
  const [value, setValue] = React.useState(initialValue);
  const [submitting, setSubmitting] = React.useState(false);

  async function handleSubmit() {
    const content = value.trim();
    if (!content) return;
    setSubmitting(true);
    try {
      await onSubmit(content);
      setValue("");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-2">
      <MentionTextarea
        value={value}
        onChange={setValue}
        members={members}
        placeholder={placeholder}
        disabled={submitting}
        autoFocus={autoFocus}
      />
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={submitting || !value.trim()}
        >
          {submitting ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button size="sm" variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
