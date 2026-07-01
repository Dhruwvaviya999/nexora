"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  aiApi,
  type AISettingsPayload,
  type ChatPayload,
  type GenerateTasksPayload,
  type PromptTemplatePayload,
  type SearchPayload,
  type SummarizePayload,
} from "@/lib/api/ai";

const KEYS = {
  conversations: (workspace?: string) =>
    ["ai", "conversations", workspace] as const,
  conversation: (id: string) => ["ai", "conversation", id] as const,
  searchHistory: (workspace?: string) =>
    ["ai", "search-history", workspace] as const,
  templates: (workspace?: string, category?: string, search?: string) =>
    ["ai", "templates", workspace, category, search] as const,
  settings: (workspace?: string) => ["ai", "settings", workspace] as const,
};

/* -------------------------------- Chat -------------------------------- */

export function useSendChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChatPayload) => aiApi.chat(payload),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["ai", "conversations"] });
      qc.invalidateQueries({ queryKey: KEYS.conversation(res.conversation) });
    },
  });
}

export function useConversations(workspace?: string) {
  return useQuery({
    queryKey: KEYS.conversations(workspace),
    queryFn: () => aiApi.listConversations(workspace as string),
    enabled: !!workspace,
  });
}

export function useConversation(id?: string) {
  return useQuery({
    queryKey: KEYS.conversation(id as string),
    queryFn: () => aiApi.getConversation(id as string),
    enabled: !!id,
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => aiApi.deleteConversation(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["ai", "conversations"] }),
  });
}

/* ------------------------------- Search ------------------------------- */

export function useSemanticSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SearchPayload) => aiApi.search(payload),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["ai", "search-history"] }),
  });
}

export function useSearchHistory(workspace?: string) {
  return useQuery({
    queryKey: KEYS.searchHistory(workspace),
    queryFn: () => aiApi.searchHistory(workspace as string),
    enabled: !!workspace,
  });
}

/* ------------------------ Summaries & action items ------------------------ */

export function useSummarize() {
  return useMutation({
    mutationFn: (payload: SummarizePayload) => aiApi.summarize(payload),
  });
}

export function useGenerateTasks() {
  return useMutation({
    mutationFn: (payload: GenerateTasksPayload) => aiApi.generateTasks(payload),
  });
}

/* --------------------------- Prompt templates --------------------------- */

export function usePromptTemplates(
  workspace?: string,
  params?: { category?: string; search?: string }
) {
  return useQuery({
    queryKey: KEYS.templates(workspace, params?.category, params?.search),
    queryFn: () => aiApi.listTemplates(workspace as string, params),
    enabled: !!workspace,
  });
}

export function useCreatePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptTemplatePayload) => aiApi.createTemplate(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai", "templates"] }),
  });
}

export function useUpdatePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Partial<PromptTemplatePayload>;
    }) => aiApi.updateTemplate(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai", "templates"] }),
  });
}

export function useDeletePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => aiApi.deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai", "templates"] }),
  });
}

/* ------------------------------ Settings ------------------------------ */

export function useAISettings(workspace?: string) {
  return useQuery({
    queryKey: KEYS.settings(workspace),
    queryFn: () => aiApi.getSettings(workspace as string),
    enabled: !!workspace,
  });
}

export function useUpdateAISettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AISettingsPayload) => aiApi.updateSettings(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai", "settings"] }),
  });
}
