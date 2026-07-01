import { z } from "zod";

export const aiSettingsSchema = z.object({
  is_enabled: z.boolean(),
  provider: z.enum(["gemini", "openai", "ollama"]),
  chat_model: z.string().min(1, "Model is required").max(128),
  temperature: z
    .number({ message: "Enter a number" })
    .min(0, "Min 0")
    .max(2, "Max 2"),
  max_tokens: z
    .number({ message: "Enter a number" })
    .int("Whole number")
    .min(1, "Min 1")
    .max(8192, "Max 8192"),
  // Optional: leaving it blank keeps the existing key.
  api_key: z.string().max(500).optional().or(z.literal("")),
});

export type AISettingsValues = z.infer<typeof aiSettingsSchema>;

export const promptTemplateSchema = z.object({
  name: z.string().min(2, "Name is too short").max(150),
  description: z.string().max(2000).optional().or(z.literal("")),
  category: z.string().max(64).optional().or(z.literal("")),
  template: z.string().min(4, "Template is too short"),
  is_shared: z.boolean(),
});

export type PromptTemplateValues = z.infer<typeof promptTemplateSchema>;
