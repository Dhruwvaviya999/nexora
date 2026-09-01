import { describe, expect, it } from "vitest";

import { cn } from "./utils";

/**
 * `cn()` is what stops two conflicting Tailwind utilities from both surviving
 * into the DOM, where CSS source order -- not the order they were written --
 * decides the winner.
 *
 * The important-modifier cases are pinned deliberately. Tailwind v4 writes
 * important as a trailing "p-2!", while tailwind-merge v2 only understood the
 * v3 leading "!p-2". Pairing the two left every `!` conflict unresolved: the
 * collapsed sidebar button kept both `p-2!` and `p-0!`, so it padded a 32px
 * button that already held a 32px logo and pushed it out of the rail.
 */
describe("cn", () => {
  it("keeps the last of two conflicting utilities", () => {
    expect(cn("p-2", "p-0")).toBe("p-0");
  });

  it("resolves conflicts written with Tailwind v4's trailing important", () => {
    expect(cn("p-2!", "p-0!")).toBe("p-0!");
    expect(cn("size-8!", "size-6!")).toBe("size-6!");
  });

  it("resolves important conflicts behind a variant prefix", () => {
    // Exactly the pair that collides on SidebarMenuButton.
    expect(
      cn(
        "group-data-[collapsible=icon]:p-2!",
        "group-data-[collapsible=icon]:p-0!"
      )
    ).toBe("group-data-[collapsible=icon]:p-0!");
  });

  it("does not merge across different variants", () => {
    const result = cn("p-2", "hover:p-0");
    expect(result).toContain("p-2");
    expect(result).toContain("hover:p-0");
  });

  it("keeps non-conflicting utilities", () => {
    expect(cn("flex", "items-center")).toBe("flex items-center");
  });

  it("drops falsy values", () => {
    expect(cn("flex", false && "hidden", undefined, null, "gap-2")).toBe(
      "flex gap-2"
    );
  });

  it("accepts conditional object syntax", () => {
    expect(cn("flex", { hidden: false, "gap-2": true })).toBe("flex gap-2");
  });
});
