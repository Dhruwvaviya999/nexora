import { z } from "zod";

/**
 * Validated, typed access to public environment variables.
 *
 * Next.js only inlines vars prefixed with `NEXT_PUBLIC_` into the client bundle,
 * so they must be referenced statically (not via a dynamic key). Validating once
 * here means a misconfigured deploy fails fast with a clear message instead of
 * producing confusing runtime errors deep in the app.
 */
const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z
    .string()
    .url("NEXT_PUBLIC_API_URL must be a valid URL")
    .default("http://localhost:8000/api/v1"),
});

const parsed = envSchema.safeParse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
});

if (!parsed.success) {
  // Surface all issues at startup rather than one-by-one at call sites.
  console.error(
    "❌ Invalid environment variables:",
    z.treeifyError(parsed.error)
  );
  throw new Error("Invalid environment variables");
}

export const env = parsed.data;
