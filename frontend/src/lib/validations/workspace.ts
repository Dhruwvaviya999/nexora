import { z } from "zod";

/** Create / update workspace form schema. */
export const workspaceSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(120, "Name is too long"),
  description: z
    .string()
    .max(2000, "Description is too long")
    .optional()
    .or(z.literal("")),
});

export type WorkspaceValues = z.infer<typeof workspaceSchema>;
