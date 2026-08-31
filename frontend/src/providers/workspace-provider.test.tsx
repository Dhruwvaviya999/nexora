import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ACTIVE_WORKSPACE_KEY,
  WorkspaceProvider,
  useWorkspaceContext,
} from "./workspace-provider";

const useWorkspaces = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-workspaces", () => ({ useWorkspaces }));

function workspace(id: string, name: string) {
  return { id, name };
}

function Probe() {
  const { activeWorkspace, activeWorkspaceId, setActiveWorkspaceId } =
    useWorkspaceContext();
  return (
    <div>
      <span data-testid="active">{activeWorkspace?.name ?? "none"}</span>
      <span data-testid="active-id">{activeWorkspaceId ?? "none"}</span>
      <button onClick={() => setActiveWorkspaceId("b")}>choose b</button>
    </div>
  );
}

function renderProvider() {
  return render(
    <WorkspaceProvider>
      <Probe />
    </WorkspaceProvider>
  );
}

describe("WorkspaceProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    useWorkspaces.mockReturnValue({
      data: { results: [workspace("a", "Alpha"), workspace("b", "Beta")] },
      isLoading: false,
    });
  });

  it("defaults to the first workspace when nothing is stored", () => {
    renderProvider();

    expect(screen.getByTestId("active")).toHaveTextContent("Alpha");
  });

  it("restores the stored workspace even when the list is already cached", () => {
    // The regression this guards: with workspaces available on the very first
    // render, a validating effect used to overwrite the restored id with the
    // first workspace before the restore had been applied.
    localStorage.setItem(ACTIVE_WORKSPACE_KEY, "b");

    renderProvider();

    expect(screen.getByTestId("active")).toHaveTextContent("Beta");
  });

  it("falls back to the first workspace when the stored one is gone", () => {
    localStorage.setItem(ACTIVE_WORKSPACE_KEY, "deleted-workspace");

    renderProvider();

    expect(screen.getByTestId("active")).toHaveTextContent("Alpha");
  });

  it("persists an explicit choice", async () => {
    const { getByText } = renderProvider();

    getByText("choose b").click();

    expect(localStorage.getItem(ACTIVE_WORKSPACE_KEY)).toBe("b");
  });

  it("reports no active workspace when the user has none", () => {
    useWorkspaces.mockReturnValue({ data: { results: [] }, isLoading: false });

    renderProvider();

    expect(screen.getByTestId("active")).toHaveTextContent("none");
    expect(screen.getByTestId("active-id")).toHaveTextContent("none");
  });

  it("survives localStorage being unavailable", () => {
    const getItem = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("storage disabled");
      });

    expect(() => renderProvider()).not.toThrow();
    expect(screen.getByTestId("active")).toHaveTextContent("Alpha");

    getItem.mockRestore();
  });

  it("throws a helpful error when used outside the provider", () => {
    // React logs the error boundary trace; keep it out of the test output.
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});

    expect(() => render(<Probe />)).toThrow(/must be used within/i);

    consoleError.mockRestore();
  });
});
