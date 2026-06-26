import { QueryClient } from "@tanstack/react-query";

/**
 * Factory for the TanStack Query client.
 *
 * A new client is created per request on the server and once on the client, so
 * server-rendered data is never shared across users. Defaults favour a SaaS
 * dashboard: don't refetch on every window focus, retry once, treat data as
 * fresh for a minute.
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  });
}
