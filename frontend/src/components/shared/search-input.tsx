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
  const onSearchRef = React.useRef(onSearch);
  onSearchRef.current = onSearch;

  // Keep local state in sync when the value is reset externally.
  React.useEffect(() => setText(value), [value]);

  React.useEffect(() => {
    const id = setTimeout(() => onSearchRef.current(text), 300);
    return () => clearTimeout(id);
  }, [text]);

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
