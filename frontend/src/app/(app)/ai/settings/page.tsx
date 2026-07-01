"use client";

import { Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { AISettingsForm } from "@/components/ai/ai-settings-form";
import { useAISettings, useUpdateAISettings } from "@/hooks/use-ai";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { getErrorMessage } from "@/lib/api/errors";
import type { AISettingsValues } from "@/lib/validations/ai";

export default function AISettingsPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: wsLoading } =
    useWorkspaceContext();
  const { data: settings, isLoading } = useAISettings(
    activeWorkspaceId ?? undefined
  );
  const update = useUpdateAISettings();

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  const isAdmin =
    activeWorkspace?.role === "owner" || activeWorkspace?.role === "admin";

  async function handleSubmit(values: AISettingsValues) {
    try {
      await update.mutateAsync({
        workspace: activeWorkspaceId as string,
        is_enabled: values.is_enabled,
        provider: values.provider,
        chat_model: values.chat_model,
        temperature: values.temperature,
        max_tokens: values.max_tokens,
        // Only send the key when the admin actually entered one.
        ...(values.api_key ? { api_key: values.api_key } : {}),
      });
      toast.success("AI settings saved");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageHeader
        title="AI settings"
        description="Configure the AI provider, model and behaviour for this workspace."
      />

      {!isAdmin && (
        <Alert>
          <ShieldAlert className="size-4" />
          <AlertTitle>Read-only</AlertTitle>
          <AlertDescription>
            Only workspace owners and admins can change AI settings.
          </AlertDescription>
        </Alert>
      )}

      {isLoading || !settings ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <AISettingsForm
              settings={settings}
              disabled={!isAdmin}
              onSubmit={handleSubmit}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
