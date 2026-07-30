"use client";

import { useRouter } from "next/navigation";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatDate } from "@/lib/format";
import { ROUTES } from "@/lib/constants";
import type { AuthUser } from "@/types/auth";
import type { Handover } from "@/types/handover";

function UserCell({ user }: { user: AuthUser | null }) {
  if (!user) return <span className="text-sm text-muted-foreground">—</span>;
  return (
    <div className="flex items-center gap-2">
      <Avatar className="size-6">
        <AvatarImage src={user.avatar || undefined} />
        <AvatarFallback className="text-xs">
          {(user.name || user.email).charAt(0).toUpperCase()}
        </AvatarFallback>
      </Avatar>
      <span className="text-sm text-muted-foreground">
        {user.name || user.email}
      </span>
    </div>
  );
}

export function HandoversTable({ handovers }: { handovers: Handover[] }) {
  const router = useRouter();

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Task</TableHead>
            <TableHead className="hidden md:table-cell">From</TableHead>
            <TableHead className="hidden md:table-cell">To</TableHead>
            <TableHead className="hidden sm:table-cell">Status</TableHead>
            <TableHead className="hidden lg:table-cell">Submitted</TableHead>
            <TableHead className="hidden lg:table-cell">Reviewed by</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {handovers.map((handover) => (
            <TableRow
              key={handover.id}
              className="cursor-pointer"
              onClick={() => router.push(ROUTES.handover(handover.id))}
            >
              <TableCell className="font-medium">{handover.task_title}</TableCell>
              <TableCell className="hidden md:table-cell">
                <UserCell user={handover.from_user} />
              </TableCell>
              <TableCell className="hidden md:table-cell">
                <UserCell user={handover.to_user} />
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <StatusBadge status={handover.status} />
              </TableCell>
              <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                {formatDate(handover.created_at)}
              </TableCell>
              <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                {handover.reviewer
                  ? handover.reviewer.name || handover.reviewer.email
                  : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
