import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/layout/site-header";
import { APP, ROUTES } from "@/lib/constants";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader />

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center gap-10 px-4 py-20 text-center">
        <div className="space-y-4">
          <span className="inline-flex items-center rounded-full border px-3 py-1 text-xs text-muted-foreground">
            Phase 1 · Foundation ready
          </span>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            {APP.name}
          </h1>
          <p className="mx-auto max-w-xl text-balance text-muted-foreground">
            {APP.description}
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button asChild>
              <Link href={ROUTES.register}>Get started</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href={ROUTES.login}>Sign in</Link>
            </Button>
          </div>
        </div>

        <div className="grid w-full gap-4 sm:grid-cols-3">
          {[
            {
              title: "Knowledge base",
              body: "Centralise docs and let AI surface answers instantly.",
            },
            {
              title: "Workflows",
              body: "Automate the busywork around your projects and tasks.",
            },
            {
              title: "Built to scale",
              body: "Modular Django + Next.js foundation, ready for what's next.",
            },
          ].map((f) => (
            <Card key={f.title} className="text-left">
              <CardHeader>
                <CardTitle className="text-base">{f.title}</CardTitle>
                <CardDescription>{f.body}</CardDescription>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Coming in a future phase.
              </CardContent>
            </Card>
          ))}
        </div>
      </main>

      <footer className="border-t py-6 text-center text-sm text-muted-foreground">
        © {APP.shortName}. Foundation scaffold.
      </footer>
    </div>
  );
}
