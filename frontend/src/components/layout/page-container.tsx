import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Page width scale.
 *
 * Without a cap, content stretches to the full viewport whenever the sidebar
 * collapses, so a table's columns jump around and long lines of text become
 * hard to track. Each page picks the width its content actually needs.
 *
 * Tune these values (or DEFAULT_PAGE_WIDTH below) and every page follows.
 */
export const PAGE_WIDTHS = {
  /** Forms and single-record settings — one column of fields. */
  sm: "max-w-2xl",
  /** Detail views: a record plus its comments/activity. */
  md: "max-w-3xl",
  /** Roomier reading width for mixed content. */
  lg: "max-w-5xl",
  /** Dashboards, tables and charts — the default. */
  xl: "max-w-7xl",
  /** Opt out: fill whatever the shell gives us. */
  full: "max-w-none",
} as const;

export type PageWidth = keyof typeof PAGE_WIDTHS;

/**
 * Applied by the app shell to every page. Change this one value to re-flow the
 * whole application; individual pages override it with <PageContainer size>.
 */
export const DEFAULT_PAGE_WIDTH: PageWidth = "xl";

/**
 * Centres page content and caps its width.
 *
 * The shell already applies DEFAULT_PAGE_WIDTH, so reach for this only when a
 * page wants something *narrower* — a form, say. Nesting is intentional and
 * harmless: the inner, smaller cap wins.
 */
export function PageContainer({
  size = DEFAULT_PAGE_WIDTH,
  className,
  children,
  ...props
}: React.ComponentProps<"div"> & { size?: PageWidth }) {
  return (
    <div className={cn("mx-auto w-full", PAGE_WIDTHS[size], className)} {...props}>
      {children}
    </div>
  );
}
