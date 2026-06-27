"use client";

import { Loader2, Mail } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RoleBadge } from "@/components/members/role-badge";
import {
  useAcceptInvitation,
  useMyInvitations,
  useRejectInvitation,
} from "@/hooks/use-invitations";
import { getErrorMessage } from "@/lib/api/errors";

export default function InvitationsPage() {
  const { data, isLoading } = useMyInvitations();
  const accept = useAcceptInvitation();
  const reject = useRejectInvitation();

  const invites = data?.results ?? [];

  async function run(promise: Promise<unknown>, message: string) {
    try {
      await promise;
      toast.success(message);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageHeader
        title="Invitations"
        description="Workspaces you've been invited to join."
      />

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : invites.length === 0 ? (
        <EmptyState
          icon={Mail}
          title="No pending invitations"
          description="When someone invites you to a workspace, it'll appear here."
        />
      ) : (
        <div className="space-y-3">
          {invites.map((inv) => (
            <Card key={inv.id}>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-base">
                    {inv.workspace_name}
                  </CardTitle>
                  <RoleBadge role={inv.role} />
                </div>
                <CardDescription>
                  Invited by {inv.invited_by.name || inv.invited_by.email}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    run(
                      accept.mutateAsync(inv.token),
                      `Joined ${inv.workspace_name}`
                    )
                  }
                >
                  Accept
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    run(reject.mutateAsync(inv.token), "Invitation declined")
                  }
                >
                  Decline
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
