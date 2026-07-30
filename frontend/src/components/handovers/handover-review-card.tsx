"use client";

import * as React from "react";
import { Check, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useReviewHandover } from "@/hooks/use-handovers";
import { getErrorMessage } from "@/lib/api/errors";
import type { Handover } from "@/types/handover";

/** Approve/reject controls, shown to workspace managers on pending handovers. */
export function HandoverReviewCard({ handover }: { handover: Handover }) {
  const review = useReviewHandover(handover.id);
  const [comment, setComment] = React.useState("");
  const [commentError, setCommentError] = React.useState("");

  async function decide(decision: "approved" | "rejected") {
    if (decision === "rejected" && !comment.trim()) {
      setCommentError("A comment is required when rejecting.");
      return;
    }
    setCommentError("");
    try {
      await review.mutateAsync({ decision, comment: comment.trim() });
      toast.success(
        decision === "approved"
          ? "Handover approved — task reassigned"
          : "Handover rejected"
      );
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Review this handover</CardTitle>
        <CardDescription>
          Approving reassigns “{handover.task_title}” to{" "}
          {handover.to_user?.name || handover.to_user?.email || "the recipient"}.
          Rejecting returns it to the submitter with your comment.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="review-comment">Comment</Label>
          <Textarea
            id="review-comment"
            rows={3}
            placeholder="Optional when approving, required when rejecting"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          {commentError ? (
            <p className="text-sm text-destructive">{commentError}</p>
          ) : null}
        </div>
        <div className="flex gap-3">
          <Button
            onClick={() => decide("approved")}
            disabled={review.isPending}
          >
            <Check className="size-4" />
            Approve
          </Button>
          <Button
            variant="destructive"
            onClick={() => decide("rejected")}
            disabled={review.isPending}
          >
            <X className="size-4" />
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
