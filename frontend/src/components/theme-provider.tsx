"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

/**
 * Wraps `next-themes` so the rest of the app imports a single local component.
 * Theme is stored in localStorage and applied via a `class` on <html>.
 */
export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
