import type { AuthUser } from "@/types/auth";

export interface DocumentItem {
  id: string;
  workspace: string;
  project: string | null;
  title: string;
  description: string;
  file_url: string | null;
  file_type: string;
  file_size: number;
  /** RAG ingestion status (Phase 5): null until first processed. */
  embedding_status: "pending" | "processing" | "completed" | "failed" | null;
  chunk_count: number;
  uploaded_by: AuthUser | null;
  created_by: AuthUser | null;
  updated_by: AuthUser | null;
  created_at: string;
  updated_at: string;
}
