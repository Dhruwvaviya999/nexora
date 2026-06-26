import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TaskPriority } from "@/types/task";

const PRIORITY_STYLES: Record<TaskPriority, { label: string; className: string }> = {
  low: { label: "Low", className: "bg-muted text-muted-foreground" },
  medium: { label: "Medium", className: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  high: { label: "High", className: "bg-amber-500/15 text-amber-600 dark:text-amber-400" },
  critical: { label: "Critical", className: "bg-rose-500/15 text-rose-600 dark:text-rose-400" },
};

export function PriorityBadge({ priority }: { priority: TaskPriority }) {
  const config = PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.medium;
  return (
    <Badge variant="secondary" className={cn("border-0 font-medium", config.className)}>
      {config.label}
    </Badge>
  );
}
