import type { Activity } from "@/types/activity";

/** Human verb for each activity action key. */
const VERBS: Record<string, string> = {
  "project.created": "created project",
  "project.updated": "updated project",
  "project.deleted": "deleted project",
  "task.created": "created task",
  "task.updated": "updated task",
  "task.deleted": "deleted task",
  "document.created": "uploaded document",
  "document.updated": "updated document",
  "document.deleted": "deleted document",
  "comment.created": "left a comment",
  "workspace.created": "created the workspace",
  "workspace.updated": "updated the workspace",
  "member.joined": "joined the workspace",
  "member.removed": "removed a member",
  "member.invited": "invited a member",
};

/** Turn an activity into a verb + the affected object's label for display. */
export function describeActivity(activity: Activity): {
  verb: string;
  label: string;
} {
  const verb = VERBS[activity.action] ?? activity.action.replace(/\./g, " ");
  const meta = activity.metadata ?? {};
  const label =
    (meta.name as string) ||
    (meta.title as string) ||
    (meta.email as string) ||
    (meta.user as string) ||
    "";
  return { verb, label };
}
