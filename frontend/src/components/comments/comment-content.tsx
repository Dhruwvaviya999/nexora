import * as React from "react";

// Matches the @[Display Name](uuid) tokens the mention input produces.
const MENTION_RE =
  /@\[([^\]]+)\]\(([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\)/g;

/** Renders comment text, turning mention tokens into highlighted chips. */
export function CommentContent({ content }: { content: string }) {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(MENTION_RE);

  while ((match = re.exec(content)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(content.slice(lastIndex, match.index));
    }
    nodes.push(
      <span
        key={`${match.index}-${match[2]}`}
        className="rounded bg-primary/10 px-1 font-medium text-primary"
      >
        @{match[1]}
      </span>
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    nodes.push(content.slice(lastIndex));
  }

  return <p className="whitespace-pre-wrap break-words text-sm">{nodes}</p>;
}
