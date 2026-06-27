import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { DocumentItem } from "@/types/document";

export type DocumentListParams = {
  workspace?: string;
  project?: string;
  search?: string;
  ordering?: string;
  page?: number;
};

export const documentsApi = {
  list: (params: DocumentListParams) =>
    apiClient.get<Paginated<DocumentItem>>(API_ROUTES.documents.list, {
      params,
    }),
  get: (id: string) =>
    apiClient.get<DocumentItem>(API_ROUTES.documents.detail(id)),
  /** Multipart upload — `form` carries the file + metadata. */
  upload: (form: FormData) =>
    apiClient.post<DocumentItem>(API_ROUTES.documents.list, form),
  update: (id: string, data: { title?: string; description?: string }) =>
    apiClient.patch<DocumentItem>(API_ROUTES.documents.detail(id), data),
  remove: (id: string) =>
    apiClient.delete<void>(API_ROUTES.documents.detail(id)),
};
