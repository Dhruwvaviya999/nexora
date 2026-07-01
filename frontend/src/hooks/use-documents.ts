"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { documentsApi, type DocumentListParams } from "@/lib/api/documents";

const KEYS = {
  all: ["documents"] as const,
  list: (params: DocumentListParams) => ["documents", "list", params] as const,
  detail: (id: string) => ["documents", id] as const,
};

export function useDocuments(params: DocumentListParams) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => documentsApi.list(params),
    enabled: !!params.workspace,
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => documentsApi.get(id),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => documentsApi.upload(form),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  });
}

/** Re-run the RAG embedding pipeline for a document (Phase 5). */
export function useReindexDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.reindex(id),
    onSuccess: (_res, id) => {
      qc.invalidateQueries({ queryKey: KEYS.detail(id) });
      qc.invalidateQueries({ queryKey: KEYS.all });
    },
  });
}
