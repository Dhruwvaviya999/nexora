import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type {
  Comment,
  CommentTargetType,
  CreateCommentInput,
} from "@/types/comment";

export const commentsApi = {
  list: (targetType: CommentTargetType, targetId: string) =>
    apiClient.get<Paginated<Comment>>(API_ROUTES.comments.list, {
      params: { target_type: targetType, target_id: targetId },
    }),

  create: (input: CreateCommentInput) =>
    apiClient.post<Comment>(API_ROUTES.comments.list, input),

  reply: (id: string, content: string) =>
    apiClient.post<Comment>(API_ROUTES.comments.reply(id), { content }),

  update: (id: string, content: string) =>
    apiClient.patch<Comment>(API_ROUTES.comments.detail(id), { content }),

  remove: (id: string) =>
    apiClient.delete<void>(API_ROUTES.comments.detail(id)),
};
