import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type {
  AuthUser,
  LoginResponse,
} from "@/types/auth";
import type { LoginValues, RegisterValues } from "@/lib/validations/auth";

/** Auth API service — thin, typed calls the hooks build on. */
export const authApi = {
  register: (data: RegisterValues) =>
    apiClient.post<AuthUser>(API_ROUTES.auth.register, data, { skipAuth: true }),

  login: (data: LoginValues) =>
    apiClient.post<LoginResponse>(API_ROUTES.auth.login, data, {
      skipAuth: true,
    }),

  logout: (refresh: string) =>
    apiClient.post<void>(API_ROUTES.auth.logout, { refresh }),

  me: () => apiClient.get<AuthUser>(API_ROUTES.auth.me),

  updateProfile: (data: { name: string; avatar?: string }) =>
    apiClient.patch<AuthUser>(API_ROUTES.auth.me, data),
};
