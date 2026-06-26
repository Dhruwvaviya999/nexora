import Link from "next/link";

import { APP } from "@/lib/constants";
import { ThemeToggle } from "@/components/theme-toggle";

/** Application shell header. Navigation items are added as features land. */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground text-sm">
            N
          </span>
          <span>{APP.shortName}</span>
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
