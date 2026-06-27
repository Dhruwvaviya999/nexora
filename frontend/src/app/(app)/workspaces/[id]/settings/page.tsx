"use client";

import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { WorkspaceForm } from "@/components/workspaces/workspace-form";
import { MemberTable } from "@/components/members/member-table";
import { InviteDialog } from "@/components/members/invite-dialog";
import { InvitationsTable } from "@/components/members/invitations-table";
import {
  useDeleteWorkspace,
  useUpdateWorkspace,
  useWorkspace,
  useWorkspaceMembers,
} from "@/hooks/use-workspaces";
import { useAuth } from "@/providers/auth-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { WorkspaceValues } from "@/lib/validations/workspace";

export default function WorkspaceSettingsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { user } = useAuth();
  const { data: workspace, isLoading } = useWorkspace(id);
  const { data: members } = useWorkspaceMembers(id);
  const updateWorkspace = useUpdateWorkspace(id);
  const deleteWorkspace = useDeleteWorkspace();

  if (isLoading || !workspace) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const canManage = workspace.role === "owner" || workspace.role === "admin";
  const isOwner = workspace.role === "owner";

  async function handleUpdate(values: WorkspaceValues) {
    try {
      await updateWorkspace.mutateAsync(values);
      toast.success("Workspace updated");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this workspace? This cannot be undone.")) return;
    try {
      await deleteWorkspace.mutateAsync(id);
      toast.success("Workspace deleted");
      router.replace(ROUTES.workspaces);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {workspace.name}
        </h1>
        <p className="text-sm text-muted-foreground">
          /{workspace.slug} · {workspace.member_count} members
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">General</CardTitle>
          <CardDescription>
            {canManage
              ? "Update your workspace details."
              : "Only admins can edit these details."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {canManage ? (
            <WorkspaceForm
              defaultValues={{
                name: workspace.name,
                description: workspace.description,
              }}
              submitLabel="Save changes"
              onSubmit={handleUpdate}
            />
          ) : (
            <p className="text-sm text-muted-foreground">{workspace.description}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <div className="space-y-1.5">
              <CardTitle className="text-base">Members</CardTitle>
              <CardDescription>
                People with access to this workspace.
              </CardDescription>
            </div>
            {canManage && <InviteDialog workspaceId={id} />}
          </div>
        </CardHeader>
        <CardContent>
          <MemberTable
            workspaceId={id}
            members={members ?? []}
            canManage={canManage}
            isOwner={isOwner}
            currentUserId={user?.id}
          />
        </CardContent>
      </Card>

      {canManage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pending invitations</CardTitle>
            <CardDescription>Invitations awaiting a response.</CardDescription>
          </CardHeader>
          <CardContent>
            <InvitationsTable workspaceId={id} />
          </CardContent>
        </Card>
      )}

      {isOwner && (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-base text-destructive">Danger zone</CardTitle>
            <CardDescription>
              Deleting a workspace is permanent and removes all its data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteWorkspace.isPending}
            >
              {deleteWorkspace.isPending ? "Deleting…" : "Delete workspace"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
