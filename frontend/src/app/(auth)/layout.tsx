import Link from "next/link";

import { APP, ROUTES } from "@/lib/constants";

/** Public, centered layout for authentication pages. */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 px-4 py-10">
      <Link href={ROUTES.home} className="flex items-center gap-2 font-semibold">
        <span className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground">
          N
        </span>
        <span className="text-lg">{APP.shortName}</span>
      </Link>
      {children}
    </div>
  );
}
