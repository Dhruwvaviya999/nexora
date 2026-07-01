"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AI_MODELS_BY_PROVIDER, AI_PROVIDERS } from "@/lib/constants";
import { aiSettingsSchema, type AISettingsValues } from "@/lib/validations/ai";
import type { AISettings } from "@/types/ai";

export function AISettingsForm({
  settings,
  disabled = false,
  onSubmit,
}: {
  settings: AISettings;
  disabled?: boolean;
  onSubmit: (values: AISettingsValues) => Promise<void> | void;
}) {
  const form = useForm<AISettingsValues>({
    resolver: zodResolver(aiSettingsSchema),
    defaultValues: {
      is_enabled: settings.is_enabled,
      provider: settings.provider,
      chat_model: settings.chat_model,
      temperature: settings.temperature,
      max_tokens: settings.max_tokens,
      api_key: "",
    },
  });

  const provider = useWatch({ control: form.control, name: "provider" });
  const modelOptions = AI_MODELS_BY_PROVIDER[provider] ?? [];

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="is_enabled"
          render={({ field }) => (
            <FormItem className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel>Enable AI assistant</FormLabel>
                <FormDescription>
                  Turn the assistant, search and summaries on or off for this
                  workspace.
                </FormDescription>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={disabled}
                />
              </FormControl>
            </FormItem>
          )}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="provider"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Provider</FormLabel>
                <Select
                  value={field.value}
                  onValueChange={(v) => {
                    field.onChange(v);
                    // Default the model to the new provider's first option.
                    const first = AI_MODELS_BY_PROVIDER[v]?.[0];
                    if (first) form.setValue("chat_model", first);
                  }}
                  disabled={disabled}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {AI_PROVIDERS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="chat_model"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Model</FormLabel>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={disabled}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {/* Ensure the current value is selectable even if custom. */}
                    {!modelOptions.includes(field.value) && field.value && (
                      <SelectItem value={field.value}>{field.value}</SelectItem>
                    )}
                    {modelOptions.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="temperature"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Temperature</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    max={2}
                    disabled={disabled}
                    name={field.name}
                    ref={field.ref}
                    onBlur={field.onBlur}
                    value={Number.isNaN(field.value) ? "" : field.value}
                    onChange={(e) => field.onChange(e.target.valueAsNumber)}
                  />
                </FormControl>
                <FormDescription>0 = focused, 2 = creative.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="max_tokens"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Max tokens</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    max={8192}
                    disabled={disabled}
                    name={field.name}
                    ref={field.ref}
                    onBlur={field.onBlur}
                    value={Number.isNaN(field.value) ? "" : field.value}
                    onChange={(e) => field.onChange(e.target.valueAsNumber)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="api_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API key</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  autoComplete="off"
                  placeholder={
                    settings.has_api_key
                      ? "•••••••• (saved — leave blank to keep)"
                      : provider === "ollama"
                        ? "Not required for Ollama"
                        : "Paste your provider API key"
                  }
                  disabled={disabled || provider === "ollama"}
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Stored encrypted. It is never displayed again after saving.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {!disabled && (
          <Button type="submit" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Saving…" : "Save settings"}
          </Button>
        )}
      </form>
    </Form>
  );
}
