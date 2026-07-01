"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RoleBadge } from "@/components/members/role-badge";
import {
  useCancelInvitation,
  useResendInvitation,
  useWorkspaceInvitations,
} from "@/hooks/use-invitations";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";

export function InvitationsTable({ workspaceId }: { workspaceId: string }) {
  const { data } = useWorkspaceInvitations(workspaceId);
  const cancel = useCancelInvitation(workspaceId);
  const resend = useResendInvitation(workspaceId);

  const pending = (data?.results ?? []).filter((i) => i.status === "pending");

  if (!pending.length) {
    return (
      <p className="text-sm text-muted-foreground">No pending invitations.</p>
    );
  }

  async function run(promise: Promise<unknown>, message: string) {
    try {
      await promise;
      toast.success(message);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Email</TableHead>
          <TableHead className="w-24">Role</TableHead>
          <TableHead className="hidden w-32 sm:table-cell">Expires</TableHead>
          <TableHead className="w-32" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {pending.map((inv) => (
          <TableRow key={inv.id}>
            <TableCell className="truncate font-medium">{inv.email}</TableCell>
            <TableCell>
              <RoleBadge role={inv.role} />
            </TableCell>
            <TableCell className="hidden text-sm text-muted-foreground sm:table-cell">
              {formatDate(inv.expires_at)}
            </TableCell>
            <TableCell>
              <div className="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() =>
                    run(resend.mutateAsync(inv.token), "Invitation resent")
                  }
                >
                  Resend
                </Button>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() =>
                    run(cancel.mutateAsync(inv.token), "Invitation cancelled")
                  }
                >
                  Cancel
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
