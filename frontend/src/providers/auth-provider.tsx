"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { authApi } from "@/lib/api/auth";
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
      if (!tokenStorage.getAccess() && !tokenStorage.getRefresh()) {
        setIsLoading(false);
        return;
      }
      try {
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
      const res = await authApi.login(credentials);
      tokenStorage.set(res.access, res.refresh);
      setUser(res.user);
    },
    []
  );

  const logout = React.useCallback(async () => {
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) await authApi.logout(refresh);
    } catch {
      // Best-effort; clear locally regardless.
    } finally {
      tokenStorage.clear();
      setUser(null);
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
