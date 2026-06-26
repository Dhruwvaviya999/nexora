import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ProjectStatus } from "@/types/project";
import type { TaskStatus } from "@/types/task";

// Tinted classes chosen to read well in both light and dark themes.
const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  // Project statuses
  planning: { label: "Planning", className: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  active: { label: "Active", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  on_hold: { label: "On hold", className: "bg-amber-500/15 text-amber-600 dark:text-amber-400" },
  // Task statuses
  todo: { label: "Todo", className: "bg-muted text-muted-foreground" },
  in_progress: { label: "In progress", className: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  review: { label: "Review", className: "bg-violet-500/15 text-violet-600 dark:text-violet-400" },
  completed: { label: "Completed", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  cancelled: { label: "Cancelled", className: "bg-rose-500/15 text-rose-600 dark:text-rose-400" },
};

export function StatusBadge({
  status,
}: {
  status: ProjectStatus | TaskStatus | string;
}) {
  const config = STATUS_STYLES[status] ?? {
    label: status,
    className: "bg-muted text-muted-foreground",
  };
  return (
    <Badge variant="secondary" className={cn("border-0 font-medium", config.className)}>
      {config.label}
    </Badge>
  );
}
