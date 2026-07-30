"""API tests for the handover workflow: submit → review (approve/reject)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.handovers.models import Handover, HandoverStatus
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

BASE = "/api/v1/handovers/"


class HandoverAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.manager = User.objects.create_user("manager@example.com", "pass12345")
        self.dev = User.objects.create_user("dev@example.com", "pass12345")
        self.teammate = User.objects.create_user("teammate@example.com", "pass12345")
        self.outsider = User.objects.create_user("outsider@example.com", "pass12345")

        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.manager, WorkspaceRole.MANAGER),
            (self.dev, WorkspaceRole.MEMBER),
            (self.teammate, WorkspaceRole.MEMBER),
        ):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=user, role=role
            )

        self.project = Project.objects.create(
            workspace=self.workspace, name="Site", created_by=self.owner
        )
        self.task = Task.objects.create(
            workspace=self.workspace,
            project=self.project,
            title="Ship checkout",
            assignee=self.dev,
            created_by=self.owner,
        )

    def _submit(self, user=None, **overrides):
        self.client.force_authenticate(user or self.dev)
        payload = {
            "task": str(self.task.id),
            "to_user_id": str(self.teammate.id),
            "summary": "Checkout flow is 80% done.",
            "pending_items": "Refund edge cases remain.",
            "resources": "See /docs/checkout.md",
            **overrides,
        }
        return self.client.post(BASE, payload, format="json")

    # -- Submission ---------------------------------------------------------

    def test_member_can_submit_handover(self):
        res = self._submit()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["status"], HandoverStatus.PENDING)
        self.assertEqual(res.data["from_user"]["id"], str(self.dev.id))
        self.assertEqual(res.data["to_user"]["id"], str(self.teammate.id))
        self.assertEqual(res.data["task_title"], "Ship checkout")

    def test_cannot_hand_over_to_self(self):
        res = self._submit(to_user_id=str(self.dev.id))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_hand_over_to_non_member(self):
        res = self._submit(to_user_id=str(self.outsider.id))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_submit(self):
        res = self._submit(user=self.outsider)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -- History ------------------------------------------------------------

    def test_history_lists_workspace_handovers(self):
        self._submit()
        self.client.force_authenticate(self.manager)
        res = self.client.get(f"{BASE}?workspace={self.workspace.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

    def test_outsider_sees_nothing(self):
        self._submit()
        self.client.force_authenticate(self.outsider)
        res = self.client.get(BASE)
        self.assertEqual(res.data["count"], 0)

    # -- Review -------------------------------------------------------------

    def _review(self, handover_id, user, decision, comment=""):
        self.client.force_authenticate(user)
        return self.client.post(
            f"{BASE}{handover_id}/review/",
            {"decision": decision, "comment": comment},
            format="json",
        )

    def test_manager_can_approve_and_task_is_reassigned(self):
        handover_id = self._submit().data["id"]
        res = self._review(handover_id, self.manager, HandoverStatus.APPROVED)
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["status"], HandoverStatus.APPROVED)
        self.assertEqual(res.data["reviewer"]["id"], str(self.manager.id))
        self.assertIsNotNone(res.data["reviewed_at"])
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee_id, self.teammate.id)

    def test_owner_can_reject_with_comment(self):
        handover_id = self._submit().data["id"]
        res = self._review(
            handover_id, self.owner, HandoverStatus.REJECTED, "Finish refunds first."
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["status"], HandoverStatus.REJECTED)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee_id, self.dev.id)  # unchanged

    def test_reject_requires_comment(self):
        handover_id = self._submit().data["id"]
        res = self._review(handover_id, self.manager, HandoverStatus.REJECTED)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_plain_member_cannot_review(self):
        handover_id = self._submit().data["id"]
        res = self._review(handover_id, self.teammate, HandoverStatus.APPROVED)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_review_twice(self):
        handover_id = self._submit().data["id"]
        self._review(handover_id, self.manager, HandoverStatus.APPROVED)
        res = self._review(handover_id, self.owner, HandoverStatus.APPROVED)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Editing / deleting -------------------------------------------------

    def test_reviewed_handover_cannot_be_edited(self):
        handover_id = self._submit().data["id"]
        self._review(handover_id, self.manager, HandoverStatus.APPROVED)
        self.client.force_authenticate(self.dev)
        res = self.client.patch(
            f"{BASE}{handover_id}/", {"summary": "Edited"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_submitter_can_edit_pending_handover(self):
        handover_id = self._submit().data["id"]
        self.client.force_authenticate(self.teammate)
        res = self.client.patch(
            f"{BASE}{handover_id}/", {"summary": "Hijacked"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_submitter_can_delete_pending_only(self):
        handover_id = self._submit().data["id"]
        self._review(handover_id, self.manager, HandoverStatus.APPROVED)
        self.client.force_authenticate(self.dev)
        res = self.client.delete(f"{BASE}{handover_id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Handover.objects.filter(pk=handover_id).exists())

    # -- PDF export ---------------------------------------------------------

    def test_member_can_export_pdf(self):
        handover_id = self._submit().data["id"]
        self.client.force_authenticate(self.manager)
        res = self.client.get(f"{BASE}{handover_id}/export/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_outsider_cannot_export_pdf(self):
        handover_id = self._submit().data["id"]
        self.client.force_authenticate(self.outsider)
        res = self.client.get(f"{BASE}{handover_id}/export/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
