"use client";

import * as React from "react";
import { MoreHorizontal } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { RoleBadge } from "@/components/members/role-badge";
import {
  useRemoveMember,
  useTransferOwnership,
  useUpdateMemberRole,
} from "@/hooks/use-members";
import { getErrorMessage } from "@/lib/api/errors";
import { initialsOf } from "@/lib/initials";
import type { WorkspaceMember } from "@/types/workspace";

interface MemberTableProps {
  workspaceId: string;
  members: WorkspaceMember[];
  canManage: boolean;
  isOwner: boolean;
  currentUserId?: string;
}

type PendingAction = { type: "remove" | "transfer"; member: WorkspaceMember };

export function MemberTable({
  workspaceId,
  members,
  canManage,
  isOwner,
  currentUserId,
}: MemberTableProps) {
  const updateRole = useUpdateMemberRole(workspaceId);
  const removeMember = useRemoveMember(workspaceId);
  const transferOwnership = useTransferOwnership(workspaceId);
  const [pending, setPending] = React.useState<PendingAction | null>(null);

  async function changeRole(member: WorkspaceMember, role: string) {
    try {
      await updateRole.mutateAsync({ memberId: member.id, role });
      toast.success("Role updated");
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  async function confirmAction() {
    if (!pending) return;
    try {
      if (pending.type === "remove") {
        await removeMember.mutateAsync(pending.member.id);
        toast.success("Member removed");
      } else {
        await transferOwnership.mutateAsync(pending.member.user.id);
        toast.success("Ownership transferred");
      }
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setPending(null);
    }
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Member</TableHead>
            <TableHead className="w-32">Role</TableHead>
            {canManage && <TableHead className="w-12" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((member) => {
            const isMemberOwner = member.role === "owner";
            const isSelf = member.user.id === currentUserId;
            const editableRole = canManage && !isMemberOwner;

            return (
              <TableRow key={member.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar className="size-8">
                      <AvatarImage src={member.user.avatar || undefined} />
                      <AvatarFallback className="text-xs">
                        {initialsOf(member.user.name, member.user.email)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {member.user.name || member.user.email}
                        {isSelf && (
                          <span className="ml-1 text-xs text-muted-foreground">
                            (you)
                          </span>
                        )}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {member.user.email}
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {editableRole ? (
                    <Select
                      defaultValue={member.role}
                      onValueChange={(role) => changeRole(member, role)}
                    >
                      <SelectTrigger size="sm" className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="member">Member</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <RoleBadge role={member.role} />
                  )}
                </TableCell>
                {canManage && (
                  <TableCell>
                    {!isMemberOwner && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon-sm">
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {isOwner && (
                            <DropdownMenuItem
                              onSelect={() =>
                                setPending({ type: "transfer", member })
                              }
                            >
                              Transfer ownership
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            variant="destructive"
                            onSelect={() => setPending({ type: "remove", member })}
                          >
                            Remove from workspace
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={!!pending}
        onOpenChange={(o) => !o && setPending(null)}
        title={
          pending?.type === "transfer"
            ? "Transfer ownership?"
            : "Remove member?"
        }
        description={
          pending?.type === "transfer"
            ? "They will become the owner and you will be demoted to admin."
            : "They will lose access to this workspace."
        }
        confirmLabel={pending?.type === "transfer" ? "Transfer" : "Remove"}
        destructive={pending?.type === "remove"}
        onConfirm={confirmAction}
      />
    </>
  );
}
