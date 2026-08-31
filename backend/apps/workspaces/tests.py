"""
Role matrix tests for workspace administration.

The README promises a specific capability split -- owner does everything,
admin manages members and invitations, manager adds handover review, member
only creates content. Tenancy and privilege escalation both live here, so each
row of that table gets an explicit test.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

WS = "/api/v1/workspaces/"
PWD = "Str0ng!Passw0rd"


class WorkspaceRoleMatrixTests(APITestCase):
    """Who may administer a workspace, and who may not."""

    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in ("owner", "admin", "manager", "member", "outsider"):
            cls.users[role] = User.objects.create_user(
                email=f"{role}@example.com", password=PWD, name=role.title()
            )

        cls.workspace = Workspace.objects.create(
            name="Role Matrix", owner=cls.users["owner"]
        )
        for role in ("owner", "admin", "manager", "member"):
            WorkspaceMember.objects.update_or_create(
                workspace=cls.workspace,
                user=cls.users[role],
                defaults={"role": getattr(WorkspaceRole, role.upper())},
            )

    def as_(self, role):
        self.client.force_authenticate(self.users[role])
        return self.client

    def member_id(self, role):
        return WorkspaceMember.objects.get(
            workspace=self.workspace, user=self.users[role]
        ).id

    # -- reading -------------------------------------------------------
    def test_every_member_can_read_the_workspace(self):
        for role in ("owner", "admin", "manager", "member"):
            with self.subTest(role=role):
                response = self.as_(role).get(f"{WS}{self.workspace.id}/")
                self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_read_the_workspace(self):
        response = self.as_("outsider").get(f"{WS}{self.workspace.id}/")
        self.assertIn(response.status_code, (403, 404))

    def test_workspace_list_is_scoped_to_membership(self):
        response = self.as_("outsider").get(WS)
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.data.get("results", response.data)]
        self.assertNotIn(str(self.workspace.id), ids)

    # -- member administration -----------------------------------------
    def test_admin_can_change_a_member_role(self):
        response = self.as_("admin").patch(
            f"{WS}{self.workspace.id}/members/{self.member_id('member')}/",
            {"role": "manager"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_plain_member_cannot_change_roles(self):
        response = self.as_("member").patch(
            f"{WS}{self.workspace.id}/members/{self.member_id('manager')}/",
            {"role": "admin"},
            format="json",
        )
        self.assertIn(response.status_code, (403, 404))

    def test_manager_cannot_change_roles(self):
        """Manager adds handover review only -- not member administration."""
        response = self.as_("manager").patch(
            f"{WS}{self.workspace.id}/members/{self.member_id('member')}/",
            {"role": "admin"},
            format="json",
        )
        self.assertIn(response.status_code, (403, 404))

    def test_member_cannot_escalate_own_role(self):
        response = self.as_("member").patch(
            f"{WS}{self.workspace.id}/members/{self.member_id('member')}/",
            {"role": "owner"},
            format="json",
        )
        self.assertIn(response.status_code, (400, 403, 404))
        self.assertEqual(
            WorkspaceMember.objects.get(
                workspace=self.workspace, user=self.users["member"]
            ).role,
            WorkspaceRole.MEMBER,
        )

    def test_owner_role_cannot_be_assigned_through_member_management(self):
        """Ownership moves only via transfer-ownership, which demotes the old owner."""
        response = self.as_("admin").patch(
            f"{WS}{self.workspace.id}/members/{self.member_id('member')}/",
            {"role": "owner"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_the_owner_membership_cannot_be_removed(self):
        response = self.as_("admin").delete(
            f"{WS}{self.workspace.id}/members/{self.member_id('owner')}/"
        )
        self.assertIn(response.status_code, (400, 403))
        self.assertTrue(
            WorkspaceMember.objects.filter(
                workspace=self.workspace, user=self.users["owner"]
            ).exists()
        )

    def test_admin_can_remove_a_member(self):
        response = self.as_("admin").delete(
            f"{WS}{self.workspace.id}/members/{self.member_id('member')}/"
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=self.workspace, user=self.users["member"]
            ).exists()
        )

    # -- ownership transfer --------------------------------------------
    def test_only_the_owner_can_transfer_ownership(self):
        for role in ("admin", "manager", "member"):
            with self.subTest(role=role):
                response = self.as_(role).post(
                    f"{WS}{self.workspace.id}/transfer-ownership/",
                    {"user_id": str(self.users["admin"].id)},
                    format="json",
                )
                self.assertIn(response.status_code, (403, 404))

    def test_owner_transfer_demotes_the_previous_owner_to_admin(self):
        response = self.as_("owner").post(
            f"{WS}{self.workspace.id}/transfer-ownership/",
            {"user_id": str(self.users["admin"].id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.owner_id, self.users["admin"].id)
        self.assertEqual(
            WorkspaceMember.objects.get(
                workspace=self.workspace, user=self.users["admin"]
            ).role,
            WorkspaceRole.OWNER,
        )
        self.assertEqual(
            WorkspaceMember.objects.get(
                workspace=self.workspace, user=self.users["owner"]
            ).role,
            WorkspaceRole.ADMIN,
        )

    def test_ownership_cannot_be_transferred_to_a_non_member(self):
        response = self.as_("owner").post(
            f"{WS}{self.workspace.id}/transfer-ownership/",
            {"user_id": str(self.users["outsider"].id)},
            format="json",
        )
        self.assertIn(response.status_code, (400, 404))
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.owner_id, self.users["owner"].id)

    # -- workspace deletion ---------------------------------------------
    def test_only_the_owner_can_delete_the_workspace(self):
        for role in ("admin", "manager", "member"):
            with self.subTest(role=role):
                response = self.as_(role).delete(f"{WS}{self.workspace.id}/")
                self.assertIn(response.status_code, (403, 404))
        self.assertTrue(Workspace.objects.filter(pk=self.workspace.pk).exists())

    def test_owner_can_delete_the_workspace(self):
        response = self.as_("owner").delete(f"{WS}{self.workspace.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Workspace.objects.filter(pk=self.workspace.pk).exists())
