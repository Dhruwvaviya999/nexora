"use client";

import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/providers/auth-provider";
import { useWorkspaces } from "@/hooks/use-workspaces";
import { ROUTES } from "@/lib/constants";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useWorkspaces();
  const workspaceCount = data?.results.length ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
          </h1>
          <p className="text-sm text-muted-foreground">
            Here&apos;s an overview of your workspaces.
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.newWorkspace}>
            <Plus className="size-4" />
            New workspace
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Workspaces</CardDescription>
            <CardTitle className="text-3xl">
              {isLoading ? "—" : workspaceCount}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Your email</CardDescription>
            <CardTitle className="truncate text-base font-medium">
              {user?.email}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Quick action</CardDescription>
            <CardTitle className="text-base font-medium">
              <Link href={ROUTES.workspaces} className="underline underline-offset-4">
                Browse workspaces
              </Link>
            </CardTitle>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
