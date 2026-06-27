/** Two-letter initials for an avatar fallback, preferring name over email. */
export function initialsOf(name?: string | null, email?: string | null): string {
  const source = (name && name.trim()) || email || "";
  return (
    source
      .split(/\s+/)
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?"
  );
}
