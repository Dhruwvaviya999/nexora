import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type {
  AuthUser,
  LoginResponse,
} from "@/types/auth";
import type {
  ForgotPasswordValues,
  LoginValues,
  RegisterValues,
  ResetPasswordValues,
} from "@/lib/validations/auth";

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

  /**
   * Ask for a reset link. Always resolves for a well-formed address, whether
   * or not an account exists -- the API deliberately refuses to say which.
   */
  requestPasswordReset: (data: ForgotPasswordValues) =>
    apiClient.post<{ detail: string }>(API_ROUTES.auth.passwordReset, data, {
      skipAuth: true,
    }),

  confirmPasswordReset: (data: ResetPasswordValues) =>
    apiClient.post<{ detail: string }>(
      API_ROUTES.auth.passwordResetConfirm,
      data,
      { skipAuth: true }
    ),
};
