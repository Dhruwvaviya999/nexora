"use client";

import * as React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import { makeQueryClient } from "@/lib/query-client";
import { ThemeProvider } from "@/components/theme-provider";

let browserQueryClient: ReturnType<typeof makeQueryClient> | undefined;

/**
 * Returns a stable QueryClient. On the server we always make a fresh one; in
 * the browser we reuse a singleton so React state changes don't blow away the
 * cache. (Recommended TanStack Query + App Router pattern.)
 */
function getQueryClient() {
  if (typeof window === "undefined") {
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

/**
 * Single client-side provider tree mounted once in the root layout: data
 * fetching (TanStack Query) + theming (next-themes).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
