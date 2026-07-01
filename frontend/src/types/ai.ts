/** AI / RAG types (mirror the backend apps.ai + apps.knowledge serializers). */

import type { AuthUser } from "@/types/auth";

export type AIProvider = "gemini" | "openai" | "ollama";
export type EmbeddingProvider = "sentence_transformer" | "gemini" | "openai";
export type MessageRole = "user" | "assistant" | "system";
export type Confidence = "high" | "medium" | "low";

/** A retrieved chunk cited by an answer / returned by semantic search. */
export interface AISource {
  chunk_id: string;
  document_id: string;
  title: string;
  content: string;
  chunk_index: number;
  score: number;
}

export interface AIMessage {
  id: string;
  conversation: string;
  role: MessageRole;
  content: string;
  sources: AISource[];
  token_count: number;
  created_at: string;
}

export interface AIConversation {
  id: string;
  workspace: string;
  user: AuthUser;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AIConversationDetail extends AIConversation {
  messages: AIMessage[];
}

/** Response of POST /ai/chat/. */
export interface ChatResponse {
  conversation: string;
  message: {
    id: string;
    role: MessageRole;
    content: string;
    sources: AISource[];
    created_at: string;
  };
  confidence: Confidence;
}

/** Response of POST /ai/search/. */
export interface SearchResponse {
  query: string;
  results: AISource[];
  count: number;
  top_score: number;
}

export interface SearchHistoryItem {
  id: string;
  workspace: string;
  query: string;
  results_count: number;
  top_score: number;
  created_at: string;
}

export type SummaryTarget = "project" | "task" | "document" | "activity";
export type SummaryPeriod = "day" | "week" | "month";

export interface SummaryResponse {
  summary: string;
  target_type: SummaryTarget;
  model: string;
}

/** A suggested task from POST /ai/generate-tasks/ (not yet persisted). */
export interface TaskSuggestion {
  title: string;
  description: string;
  priority: "low" | "medium" | "high" | "critical";
  due_date: string | null;
}

export interface GenerateTasksResponse {
  suggestions: TaskSuggestion[];
  model: string;
}

export interface PromptTemplate {
  id: string;
  workspace: string;
  name: string;
  description: string;
  category: string;
  template: string;
  is_shared: boolean;
  created_by: AuthUser | null;
  created_at: string;
  updated_at: string;
}

export interface AISettings {
  id: string;
  workspace: string;
  is_enabled: boolean;
  provider: AIProvider;
  chat_model: string;
  embedding_provider: EmbeddingProvider;
  embedding_model: string;
  temperature: number;
  max_tokens: number;
  /** Whether an encrypted API key is stored (the key itself is never returned). */
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}
