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

/**
 * POST /auth/login/ response.
 *
 * There is no `refresh` field: the backend moves the refresh token into an
 * httpOnly cookie so page script can never read it. Only the short-lived
 * access token reaches JavaScript, and it is kept in memory.
 */
export interface LoginResponse {
  access: string;
  user: AuthUser;
}

/**
 * POST /auth/refresh/ response.
 *
 * Rotation is on, but the rotated refresh token is written straight back to
 * the httpOnly cookie — it never appears in the body.
 */
export interface RefreshResponse {
  access: string;
}
