"use client";

import * as React from "react";

import { useWorkspaces } from "@/hooks/use-workspaces";
import { STORAGE_KEYS } from "@/lib/constants";
import type { Workspace } from "@/types/workspace";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string) => void;
  isLoading: boolean;
}

const ACTIVE_KEY = "nexora.activeWorkspace";

const WorkspaceContext = React.createContext<WorkspaceContextValue | undefined>(
  undefined
);

/**
 * Tracks the "current" workspace across the app. Every list query is scoped to
 * it. The choice is persisted in localStorage and defaults to the first
 * workspace the user belongs to.
 */
export function WorkspaceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data, isLoading } = useWorkspaces();
  const workspaces = React.useMemo(() => data?.results ?? [], [data]);
  const [activeId, setActiveId] = React.useState<string | null>(null);

  // Restore the persisted selection once on mount.
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      setActiveId(window.localStorage.getItem(ACTIVE_KEY));
    }
  }, []);

  // Ensure the active id is always a workspace the user can still access.
  React.useEffect(() => {
    if (!workspaces.length) return;
    const stillValid = activeId && workspaces.some((w) => w.id === activeId);
    if (!stillValid) {
      setActiveId(workspaces[0].id);
    }
  }, [workspaces, activeId]);

  const setActiveWorkspaceId = React.useCallback((id: string) => {
    setActiveId(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACTIVE_KEY, id);
    }
  }, []);

  const value = React.useMemo<WorkspaceContextValue>(() => {
    const activeWorkspace =
      workspaces.find((w) => w.id === activeId) ?? null;
    return {
      workspaces,
      activeWorkspace,
      activeWorkspaceId: activeWorkspace?.id ?? null,
      setActiveWorkspaceId,
      isLoading,
    };
  }, [workspaces, activeId, setActiveWorkspaceId, isLoading]);

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspaceContext(): WorkspaceContextValue {
  const ctx = React.useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error(
      "useWorkspaceContext must be used within a <WorkspaceProvider>."
    );
  }
  return ctx;
}

// Re-export the storage key namespace for discoverability.
export { ACTIVE_KEY as ACTIVE_WORKSPACE_KEY, STORAGE_KEYS };
