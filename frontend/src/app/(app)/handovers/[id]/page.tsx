"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, FileDown, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { HandoverReviewCard } from "@/components/handovers/handover-review-card";
import { useAuth } from "@/providers/auth-provider";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useDeleteHandover, useHandover } from "@/hooks/use-handovers";
import { downloadFile } from "@/lib/api/download";
import { getErrorMessage } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";
import { API_ROUTES, ROUTES } from "@/lib/constants";
import { REVIEWER_ROLES } from "@/types/workspace";
import type { AuthUser } from "@/types/auth";

import { PageContainer } from "@/components/layout/page-container";
function UserChip({ user, fallback }: { user: AuthUser | null; fallback: string }) {
  if (!user) return <span className="text-muted-foreground">{fallback}</span>;
  return (
    <span className="flex items-center gap-2">
      <Avatar className="size-6">
        <AvatarImage src={user.avatar || undefined} />
        <AvatarFallback className="text-xs">
          {(user.name || user.email).charAt(0).toUpperCase()}
        </AvatarFallback>
      </Avatar>
      {user.name || user.email}
    </span>
  );
}

function TextSection({ title, text }: { title: string; text: string }) {
  if (!text) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm">{text}</p>
      </CardContent>
    </Card>
  );
}

export default function HandoverDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const { activeWorkspace } = useWorkspaceContext();
  const { data: handover, isLoading } = useHandover(id);
  const deleteHandover = useDeleteHandover();
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const [exporting, setExporting] = React.useState(false);

  if (isLoading || !handover) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const canReview =
    !!activeWorkspace?.role && REVIEWER_ROLES.includes(activeWorkspace.role);
  const isSubmitter = !!user && handover.from_user?.id === user.id;
  const isPending = handover.status === "pending";

  async function onDelete() {
    if (!handover) return;
    try {
      await deleteHandover.mutateAsync(handover.id);
      toast.success("Handover deleted");
      router.replace(ROUTES.handovers);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <PageContainer size="md" className="space-y-6">
      <PageHeader
        title={`Handover: ${handover.task_title}`}
        description="A request to transfer this task to a teammate."
      >
        <Button
          variant="outline"
          disabled={exporting}
          onClick={async () => {
            setExporting(true);
            try {
              await downloadFile(
                API_ROUTES.handovers.export(handover.id),
                "handover.pdf"
              );
            } catch {
              toast.error("Export failed");
            } finally {
              setExporting(false);
            }
          }}
        >
          <FileDown className="size-4" />
          {exporting ? "Exporting…" : "Export PDF"}
        </Button>
        {isPending && (isSubmitter || canReview) ? (
          <Button variant="outline" onClick={() => setConfirmDelete(true)}>
            <Trash2 className="size-4" />
            Delete
          </Button>
        ) : null}
      </PageHeader>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Details</CardTitle>
          <StatusBadge status={handover.status} />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <UserChip user={handover.from_user} fallback="Unknown" />
            <ArrowRight className="size-4 text-muted-foreground" />
            <UserChip user={handover.to_user} fallback="Unknown" />
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Task
              </p>
              <Link
                href={ROUTES.task(handover.task)}
                className="text-sm font-medium underline-offset-4 hover:underline"
              >
                {handover.task_title}
              </Link>
            </div>
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Submitted
              </p>
              <p className="text-sm">{formatDate(handover.created_at)}</p>
            </div>
            {handover.reviewer ? (
              <>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Reviewed by
                  </p>
                  <div className="text-sm">
                    <UserChip user={handover.reviewer} fallback="—" />
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Reviewed at
                  </p>
                  <p className="text-sm">{formatDate(handover.reviewed_at)}</p>
                </div>
              </>
            ) : null}
          </div>
          {handover.review_comment ? (
            <>
              <Separator />
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Review comment
                </p>
                <p className="whitespace-pre-wrap text-sm">
                  {handover.review_comment}
                </p>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <TextSection title="Work summary" text={handover.summary} />
      <TextSection title="Pending items" text={handover.pending_items} />
      <TextSection title="Resources" text={handover.resources} />

      {isPending && canReview ? <HandoverReviewCard handover={handover} /> : null}

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete handover?"
        description="This pending handover will be permanently removed."
        onConfirm={onDelete}
      />
    </PageContainer>
  );
}
