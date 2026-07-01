import { z } from "zod";

export const projectSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(150, "Name is too long"),
  description: z.string().max(2000).optional().or(z.literal("")),
  color: z
    .string()
    .regex(/^#([0-9a-fA-F]{6})$/, "Use a hex colour like #6366f1")
    .optional()
    .or(z.literal("")),
  status: z.enum(["planning", "active", "on_hold", "completed"]),
});

export type ProjectValues = z.infer<typeof projectSchema>;
