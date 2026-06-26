/** Authentication & user types (mirror the backend serializers). */

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatar: string;
  is_active: boolean;
  date_joined: string;
  created_at: string;
  updated_at: string;
}

/** JWT pair returned by the login endpoint. */
export interface TokenPair {
  access: string;
  refresh: string;
}

/** POST /auth/login/ response. */
export interface LoginResponse extends TokenPair {
  user: AuthUser;
}

/** POST /auth/refresh/ response (ROTATE_REFRESH_TOKENS returns a new refresh too). */
export interface RefreshResponse {
  access: string;
  refresh?: string;
}
