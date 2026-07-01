import { env } from "@/config/env";

/** App-wide static metadata. */
export const APP = {
  name: "AI Knowledge & Workflow Assistant",
  shortName: "Nexora",
  description:
    "Your team's knowledge base and workflow automation, powered by AI.",
} as const;

/** Base URL of the versioned backend API (e.g. http://localhost:8000/api/v1). */
export const API_BASE_URL = env.NEXT_PUBLIC_API_URL;

/**
 * Centralised API route builders. Keep every endpoint path here so callers
 * never hard-code strings and future renames happen in one place.
 */
export const API_ROUTES = {
  health: "/health/",
  auth: {
    register: "/auth/register/",
    login: "/auth/login/",
    refresh: "/auth/refresh/",
    logout: "/auth/logout/",
    me: "/auth/me/",
  },
  workspaces: {
    list: "/workspaces/",
    detail: (id: string) => `/workspaces/${id}/`,
    members: (id: string) => `/workspaces/${id}/members/`,
    member: (id: string, memberId: string) =>
      `/workspaces/${id}/members/${memberId}/`,
    transferOwnership: (id: string) => `/workspaces/${id}/transfer-ownership/`,
  },
  comments: {
    list: "/comments/",
    detail: (id: string) => `/comments/${id}/`,
    reply: (id: string) => `/comments/${id}/reply/`,
  },
  notifications: {
    list: "/notifications/",
    read: (id: string) => `/notifications/${id}/read/`,
    readAll: "/notifications/read-all/",
    unreadCount: "/notifications/unread-count/",
  },
  activities: "/activities/",
  invitations: {
    list: "/invitations/",
    detail: (token: string) => `/invitations/${token}/`,
    accept: (token: string) => `/invitations/${token}/accept/`,
    reject: (token: string) => `/invitations/${token}/reject/`,
    resend: (token: string) => `/invitations/${token}/resend/`,
  },
  dashboard: "/dashboard/",
  projects: {
    list: "/projects/",
    detail: (id: string) => `/projects/${id}/`,
    archive: (id: string) => `/projects/${id}/archive/`,
    restore: (id: string) => `/projects/${id}/restore/`,
  },
  tasks: {
    list: "/tasks/",
    detail: (id: string) => `/tasks/${id}/`,
  },
  documents: {
    list: "/documents/",
    detail: (id: string) => `/documents/${id}/`,
    reindex: (id: string) => `/documents/${id}/reindex/`,
  },
  ai: {
    chat: "/ai/chat/",
    search: "/ai/search/",
    summarize: "/ai/summarize/",
    generateTasks: "/ai/generate-tasks/",
    settings: "/ai/settings/",
    conversations: "/ai/conversations/",
    conversation: (id: string) => `/ai/conversations/${id}/`,
    searchHistory: "/ai/search-history/",
    promptTemplates: "/ai/prompt-templates/",
    promptTemplate: (id: string) => `/ai/prompt-templates/${id}/`,
  },
} as const;

/** Client-side route paths used for navigation and guards. */
export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  workspaces: "/workspaces",
  newWorkspace: "/workspaces/new",
  workspaceSettings: (id: string) => `/workspaces/${id}/settings`,
  projects: "/projects",
  newProject: "/projects/new",
  project: (id: string) => `/projects/${id}`,
  editProject: (id: string) => `/projects/${id}/edit`,
  tasks: "/tasks",
  newTask: "/tasks/new",
  task: (id: string) => `/tasks/${id}`,
  editTask: (id: string) => `/tasks/${id}/edit`,
  documents: "/documents",
  newDocument: "/documents/new",
  document: (id: string) => `/documents/${id}`,
  search: "/search",
  settings: "/settings",
  notifications: "/notifications",
  activity: "/activity",
  invitations: "/invitations",
  // AI Knowledge Assistant (Phase 5)
  ai: "/ai",
  aiChat: "/ai/chat",
  aiConversation: (id: string) => `/ai/chat/${id}`,
  aiConversations: "/ai/conversations",
  aiSearch: "/ai/search",
  aiTemplates: "/ai/templates",
  aiSettings: "/ai/settings",
} as const;

/** Provider/model options surfaced in the AI settings form. */
export const AI_PROVIDERS = [
  { value: "gemini", label: "Gemini (Google)" },
  { value: "openai", label: "OpenAI" },
  { value: "ollama", label: "Ollama (local)" },
] as const;

/** Suggested default chat models per provider (free-text is also allowed). */
export const AI_MODELS_BY_PROVIDER: Record<string, string[]> = {
  gemini: ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
  ollama: ["llama3.1", "llama3.2", "mistral", "qwen2.5"],
};

/** Display metadata for the enum values shared by the backend. */
export const PROJECT_STATUSES = [
  { value: "planning", label: "Planning" },
  { value: "active", label: "Active" },
  { value: "on_hold", label: "On hold" },
  { value: "completed", label: "Completed" },
] as const;

export const TASK_STATUSES = [
  { value: "todo", label: "Todo" },
  { value: "in_progress", label: "In progress" },
  { value: "review", label: "Review" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
] as const;

export const TASK_PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
] as const;

/** Default page size mirrors DRF's PAGE_SIZE. */
export const PAGE_SIZE = 20;

/** localStorage / cookie keys (auth tokens land here in Phase 2). */
export const STORAGE_KEYS = {
  accessToken: "nexora.accessToken",
  refreshToken: "nexora.refreshToken",
  theme: "nexora.theme",
} as const;
