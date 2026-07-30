"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { HandoverForm } from "@/components/handovers/handover-form";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { useCreateHandover } from "@/hooks/use-handovers";
import { toHandoverPayload } from "@/lib/api/handovers";
import { getErrorMessage } from "@/lib/api/errors";
import { ROUTES } from "@/lib/constants";
import type { HandoverValues } from "@/lib/validations/handover";

function NewHandoverInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { activeWorkspaceId } = useWorkspaceContext();
  const createHandover = useCreateHandover();

  if (!activeWorkspaceId) return <NoWorkspace />;

  async function handleSubmit(values: HandoverValues) {
    try {
      const handover = await createHandover.mutateAsync(
        toHandoverPayload(values)
      );
      toast.success("Handover submitted for review");
      router.replace(ROUTES.handover(handover.id));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <PageHeader
        title="New handover"
        description="Hand a task over to a teammate. A manager reviews it before the task is reassigned."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Handover details</CardTitle>
        </CardHeader>
        <CardContent>
          <HandoverForm
            workspaceId={activeWorkspaceId}
            defaultValues={{ task: searchParams.get("task") ?? "" }}
            submitLabel="Submit handover"
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </div>
  );
}

export default function NewHandoverPage() {
  return (
    <Suspense fallback={null}>
      <NewHandoverInner />
    </Suspense>
  );
}
