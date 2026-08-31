import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchInput } from "./search-input";

/**
 * These assert the debounce contract, so they drive the input with
 * fireEvent and a fake clock rather than userEvent -- typing through
 * userEvent while timers are mocked deadlocks the two against each other.
 */
describe("SearchInput", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const type = (text: string) =>
    act(() => {
      fireEvent.change(screen.getByRole("textbox"), { target: { value: text } });
    });

  const advance = (ms: number) =>
    act(() => {
      vi.advanceTimersByTime(ms);
    });

  it("does not search on mount", () => {
    const onSearch = vi.fn();
    render(<SearchInput value="" onSearch={onSearch} />);

    advance(1000);

    expect(onSearch).not.toHaveBeenCalled();
  });

  it("waits for the typing to stop before searching", () => {
    const onSearch = vi.fn();
    render(<SearchInput value="" onSearch={onSearch} />);

    type("bug");
    advance(299);
    expect(onSearch).not.toHaveBeenCalled();

    advance(1);
    expect(onSearch).toHaveBeenCalledExactlyOnceWith("bug");
  });

  it("collapses a burst of keystrokes into one search", () => {
    const onSearch = vi.fn();
    render(<SearchInput value="" onSearch={onSearch} />);

    type("r");
    advance(100);
    type("re");
    advance(100);
    type("rep");
    advance(300);

    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith("rep");
  });

  it("adopts a value reset from outside without searching for it again", () => {
    const onSearch = vi.fn();
    const { rerender } = render(<SearchInput value="old" onSearch={onSearch} />);

    rerender(<SearchInput value="" onSearch={onSearch} />);
    advance(1000);

    expect(screen.getByRole("textbox")).toHaveValue("");
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("uses the latest callback, not the one captured when typing began", () => {
    const stale = vi.fn();
    const fresh = vi.fn();
    const { rerender } = render(<SearchInput value="" onSearch={stale} />);

    type("x");
    rerender(<SearchInput value="" onSearch={fresh} />);
    advance(300);

    expect(stale).not.toHaveBeenCalled();
    expect(fresh).toHaveBeenCalledWith("x");
  });

  it("renders the placeholder it is given", () => {
    render(
      <SearchInput value="" onSearch={vi.fn()} placeholder="Find a task" />
    );

    expect(screen.getByPlaceholderText("Find a task")).toBeInTheDocument();
  });
});
