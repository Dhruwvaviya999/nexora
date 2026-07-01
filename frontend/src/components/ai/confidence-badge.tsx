import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Confidence } from "@/types/ai";

const CONFIG: Record<
  Confidence,
  { label: string; className: string; Icon: typeof ShieldCheck }
> = {
  high: {
    label: "High confidence",
    className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    Icon: ShieldCheck,
  },
  medium: {
    label: "Medium confidence",
    className: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    Icon: ShieldQuestion,
  },
  low: {
    label: "Low confidence",
    className: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    Icon: ShieldAlert,
  },
};

/** Visual indicator of how well the answer is grounded in workspace sources. */
export function ConfidenceBadge({
  confidence,
  className,
}: {
  confidence: Confidence;
  className?: string;
}) {
  const { label, className: tint, Icon } = CONFIG[confidence] ?? CONFIG.low;
  return (
    <Badge
      variant="secondary"
      className={cn("gap-1 border-0 font-medium", tint, className)}
    >
      <Icon className="size-3" />
      {label}
    </Badge>
  );
}
