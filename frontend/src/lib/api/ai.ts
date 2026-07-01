import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type {
  AIConversation,
  AIConversationDetail,
  AISettings,
  ChatResponse,
  GenerateTasksResponse,
  PromptTemplate,
  SearchHistoryItem,
  SearchResponse,
  SummaryPeriod,
  SummaryResponse,
  SummaryTarget,
} from "@/types/ai";

export interface ChatPayload {
  workspace: string;
  conversation?: string;
  message: string;
}

export interface SearchPayload {
  workspace: string;
  query: string;
  limit?: number;
}

export interface SummarizePayload {
  workspace: string;
  target_type: SummaryTarget;
  target_id?: string;
  period?: SummaryPeriod;
}

export interface GenerateTasksPayload {
  workspace: string;
  document?: string;
  text?: string;
}

export interface PromptTemplatePayload {
  workspace: string;
  name: string;
  description?: string;
  category?: string;
  template: string;
  is_shared?: boolean;
}

export type AISettingsPayload = Partial<{
  workspace: string;
  is_enabled: boolean;
  provider: string;
  chat_model: string;
  embedding_provider: string;
  embedding_model: string;
  temperature: number;
  max_tokens: number;
  api_key: string;
}>;

export const aiApi = {
  chat: (payload: ChatPayload) =>
    apiClient.post<ChatResponse>(API_ROUTES.ai.chat, payload),

  search: (payload: SearchPayload) =>
    apiClient.post<SearchResponse>(API_ROUTES.ai.search, payload),

  summarize: (payload: SummarizePayload) =>
    apiClient.post<SummaryResponse>(API_ROUTES.ai.summarize, payload),

  generateTasks: (payload: GenerateTasksPayload) =>
    apiClient.post<GenerateTasksResponse>(
      API_ROUTES.ai.generateTasks,
      payload
    ),

  // -- Conversations --
  listConversations: (workspace: string, page = 1) =>
    apiClient.get<Paginated<AIConversation>>(API_ROUTES.ai.conversations, {
      params: { workspace, page },
    }),
  getConversation: (id: string) =>
    apiClient.get<AIConversationDetail>(API_ROUTES.ai.conversation(id)),
  deleteConversation: (id: string) =>
    apiClient.delete<void>(API_ROUTES.ai.conversation(id)),

  // -- Search history --
  searchHistory: (workspace: string) =>
    apiClient.get<Paginated<SearchHistoryItem>>(API_ROUTES.ai.searchHistory, {
      params: { workspace },
    }),

  // -- Prompt templates --
  listTemplates: (workspace: string, params?: { category?: string; search?: string }) =>
    apiClient.get<Paginated<PromptTemplate>>(API_ROUTES.ai.promptTemplates, {
      params: { workspace, ...params },
    }),
  createTemplate: (payload: PromptTemplatePayload) =>
    apiClient.post<PromptTemplate>(API_ROUTES.ai.promptTemplates, payload),
  updateTemplate: (id: string, payload: Partial<PromptTemplatePayload>) =>
    apiClient.patch<PromptTemplate>(API_ROUTES.ai.promptTemplate(id), payload),
  deleteTemplate: (id: string) =>
    apiClient.delete<void>(API_ROUTES.ai.promptTemplate(id)),

  // -- Settings --
  getSettings: (workspace: string) =>
    apiClient.get<AISettings>(API_ROUTES.ai.settings, { params: { workspace } }),
  updateSettings: (payload: AISettingsPayload) =>
    apiClient.patch<AISettings>(API_ROUTES.ai.settings, payload),
};
