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

/** Other tabs switching workspace; same-tab writes go through React state. */
function subscribeToStoredWorkspace(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function readStoredWorkspace(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_KEY);
  } catch {
    // Private mode, or storage disabled -- fall back to the first workspace.
    return null;
  }
}

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

  const storedId = React.useSyncExternalStore(
    subscribeToStoredWorkspace,
    readStoredWorkspace,
    () => null
  );
  // Set by an explicit in-app choice, which takes precedence over what is
  // stored (a same-tab localStorage write raises no "storage" event).
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const setActiveWorkspaceId = React.useCallback((id: string) => {
    setSelectedId(id);
    try {
      window.localStorage.setItem(ACTIVE_KEY, id);
    } catch {
      // Persistence is a convenience; the in-memory choice still applies.
    }
  }, []);

  const value = React.useMemo<WorkspaceContextValue>(() => {
    // Resolved during render rather than corrected afterwards by an effect.
    // The previous effect pair could race -- restoring the persisted id and
    // then immediately overwriting it with the first workspace, because the
    // validating effect still saw the pre-restore value.
    const preferredId = selectedId ?? storedId;
    const activeWorkspace =
      workspaces.find((w) => w.id === preferredId) ?? workspaces[0] ?? null;

    return {
      workspaces,
      activeWorkspace,
      activeWorkspaceId: activeWorkspace?.id ?? null,
      setActiveWorkspaceId,
      isLoading,
    };
  }, [workspaces, selectedId, storedId, setActiveWorkspaceId, isLoading]);

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
