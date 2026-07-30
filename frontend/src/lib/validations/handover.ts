import { z } from "zod";

export const handoverSchema = z.object({
  task: z.string().min(1, "Select a task"),
  to_user_id: z.string().min(1, "Select who takes over"),
  summary: z
    .string()
    .min(10, "Describe the work done (at least 10 characters)")
    .max(5000),
  pending_items: z.string().max(5000).optional().or(z.literal("")),
  resources: z.string().max(5000).optional().or(z.literal("")),
});

export type HandoverValues = z.infer<typeof handoverSchema>;

export const handoverReviewSchema = z
  .object({
    decision: z.enum(["approved", "rejected"]),
    comment: z.string().max(5000).optional().or(z.literal("")),
  })
  .refine((v) => v.decision !== "rejected" || (v.comment ?? "").trim().length > 0, {
    message: "A comment is required when rejecting",
    path: ["comment"],
  });

export type HandoverReviewValues = z.infer<typeof handoverReviewSchema>;
