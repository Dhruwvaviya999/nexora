"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

/** Debounced search box. Calls `onSearch` ~300ms after typing stops. */
export function SearchInput({
  value,
  onSearch,
  placeholder = "Search…",
  className,
}: {
  value: string;
  onSearch: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  const [text, setText] = React.useState(value);

  // Latest callback, so the debounce timer never closes over a stale one.
  // Assigned in an effect rather than during render, which would be a side
  // effect in the render phase.
  const onSearchRef = React.useRef(onSearch);
  React.useEffect(() => {
    onSearchRef.current = onSearch;
  });

  // Adopt the value when it is reset externally (a "clear filters" button, say).
  // Adjusting state during render is the supported pattern here; doing it in an
  // effect would render the stale text once first.
  const [syncedValue, setSyncedValue] = React.useState(value);
  if (value !== syncedValue) {
    setSyncedValue(value);
    setText(value);
  }

  React.useEffect(() => {
    // Already in step with the parent -- on mount, or just after an external
    // reset. Firing would issue a redundant search for what is already shown.
    if (text === value) return;
    const id = setTimeout(() => onSearchRef.current(text), 300);
    return () => clearTimeout(id);
  }, [text, value]);

  return (
    <div className={className}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
          className="pl-8"
        />
      </div>
    </div>
  );
}
