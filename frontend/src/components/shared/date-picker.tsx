"use client";

import { CalendarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";

/** Date picker built on shadcn Popover + Calendar. Value is an ISO `YYYY-MM-DD` string. */
export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
}: {
  value?: string | null;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const selected = value ? new Date(value) : undefined;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn(
            "w-full justify-start font-normal",
            !value && "text-muted-foreground"
          )}
        >
          <CalendarIcon className="size-4" />
          {value ? formatDate(value) : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selected}
          onSelect={(date) =>
            onChange(date ? date.toISOString().slice(0, 10) : "")
          }
          autoFocus
        />
      </PopoverContent>
    </Popover>
  );
}
