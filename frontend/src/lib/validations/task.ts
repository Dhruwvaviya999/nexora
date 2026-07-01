import { z } from "zod";

export const taskSchema = z.object({
  project: z.string().min(1, "Select a project"),
  title: z
    .string()
    .min(2, "Title must be at least 2 characters")
    .max(255, "Title is too long"),
  description: z.string().max(5000).optional().or(z.literal("")),
  status: z.enum(["todo", "in_progress", "review", "completed", "cancelled"]),
  priority: z.enum(["low", "medium", "high", "critical"]),
  assignee_id: z.string().optional().or(z.literal("")),
  due_date: z.string().optional().or(z.literal("")),
  start_date: z.string().optional().or(z.literal("")),
  estimated_hours: z.string().optional().or(z.literal("")),
  labels: z.array(z.string()).optional(),
});

export type TaskValues = z.infer<typeof taskSchema>;
