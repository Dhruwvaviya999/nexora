"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { authApi } from "@/lib/api/auth";
import { ensureAccessToken } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/token-storage";
import { ROUTES } from "@/lib/constants";
import type { AuthUser } from "@/types/auth";
import type { LoginValues } from "@/lib/validations/auth";

interface AuthContextValue {
  user: AuthUser | null;
  /** True until the initial "am I logged in?" check resolves. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginValues) => Promise<void>;
  logout: () => Promise<void>;
  /** Update the cached user after a profile edit. */
  setUser: (user: AuthUser) => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

/**
 * Holds authentication state for the app. On mount, if a token exists it
 * fetches the current user; the API client handles silent token refresh.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    async function bootstrap() {
      // A reload wipes the in-memory access token but leaves the httpOnly
      // refresh cookie, so "am I logged in?" means "can I still refresh?".
      // The session flag is a cheap pre-check that avoids a guaranteed-404
      // refresh call for a visitor who has never signed in; it holds no
      // secret and is not trusted for anything else.
      if (!tokenStorage.getAccess() && !tokenStorage.hasSessionFlag()) {
        setIsLoading(false);
        return;
      }
      try {
        // Mints an access token from the refresh cookie when memory is empty.
        const token = await ensureAccessToken();
        if (!token) throw new Error("No session");
        const me = await authApi.me();
        if (active) setUser(me);
      } catch {
        tokenStorage.clear();
      } finally {
        if (active) setIsLoading(false);
      }
    }
    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  const login = React.useCallback(
    async (credentials: LoginValues) => {
      // The response carries only the access token; the refresh token arrives
      // as an httpOnly cookie the browser stores for us.
      const res = await authApi.login(credentials);
      tokenStorage.setAccess(res.access);
      setUser(res.user);
    },
    []
  );

  const logout = React.useCallback(async () => {
    try {
      // The server reads the refresh cookie, blacklists it and clears it.
      await authApi.logout();
    } catch {
      // Best-effort; clear locally regardless so the user is never stuck
      // "logged in" against an unreachable server.
    } finally {
      tokenStorage.clear();
      setUser(null);
      // Without this the next person to sign in on this browser would briefly
      // see the previous user's cached lists.
      queryClient.clear();
      router.replace(ROUTES.login);
    }
  }, [queryClient, router]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      setUser,
    }),
    [user, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>.");
  }
  return ctx;
}
