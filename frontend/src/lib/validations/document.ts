import { z } from "zod";

export const documentSchema = z.object({
  title: z.string().max(255).optional().or(z.literal("")),
  description: z.string().max(2000).optional().or(z.literal("")),
  project: z.string().optional().or(z.literal("")),
  file: z
    .instanceof(File, { message: "A file is required" })
    .refine((f) => f.size > 0, "A file is required"),
});

export type DocumentValues = z.infer<typeof documentSchema>;
