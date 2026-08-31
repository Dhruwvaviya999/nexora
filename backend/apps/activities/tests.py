"""
Activity logging tests.

The audit trail is wired through signals, which means it also fires during
cascade deletes. Deleting a workspace cascades into every child object, so the
handlers must not append rows pointing at the workspace that is on its way out.
``TransactionTestCase`` is used deliberately: the failure this guards against
is a deferred foreign key check that only surfaces on a real commit.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.activities.models import Activity
from apps.documents.models import Document
from apps.handovers.models import Handover
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

PWD = "Str0ng!Passw0rd"


class WorkspaceDeletionActivityTests(TransactionTestCase):
    """Deleting a populated workspace must commit cleanly."""

    reset_sequences = True

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password=PWD, name="Owner"
        )
        self.teammate = User.objects.create_user(
            email="teammate@example.com", password=PWD, name="Teammate"
        )
        self.workspace = Workspace.objects.create(name="Doomed", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.teammate, WorkspaceRole.MEMBER),
        ):
            WorkspaceMember.objects.update_or_create(
                workspace=self.workspace, user=user, defaults={"role": role}
            )

        project = Project.objects.create(
            workspace=self.workspace, name="Doomed Project", created_by=self.owner
        )
        task = Task.objects.create(
            workspace=self.workspace,
            project=project,
            title="Doomed Task",
            created_by=self.owner,
        )
        Document.objects.create(
            workspace=self.workspace, title="Doomed Doc", uploaded_by=self.owner
        )
        Handover.objects.create(
            workspace=self.workspace,
            task=task,
            from_user=self.teammate,
            to_user=self.owner,
            summary="Handing over.",
            created_by=self.teammate,
        )

    def test_orm_delete_of_a_populated_workspace_commits(self):
        """A cascade delete must not leave activity rows behind."""
        workspace_id = self.workspace.id

        self.workspace.delete()

        self.assertFalse(Workspace.objects.filter(pk=workspace_id).exists())
        self.assertFalse(
            Activity.objects.filter(workspace_id=workspace_id).exists(),
            "activity rows survived their workspace and now dangle",
        )

    def test_api_delete_of_a_populated_workspace_returns_204(self):
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.delete(f"/api/v1/workspaces/{self.workspace.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Workspace.objects.filter(pk=self.workspace.pk).exists())

    def test_ordinary_deletes_are_still_recorded(self):
        """The suppression must be scoped to workspace deletion only."""
        project = Project.objects.create(
            workspace=self.workspace, name="Temporary", created_by=self.owner
        )
        Activity.objects.filter(workspace=self.workspace).delete()

        project.delete()

        self.assertTrue(
            Activity.objects.filter(
                workspace=self.workspace, action="project.deleted"
            ).exists(),
            "deleting a project no longer writes an audit row",
        )

    def tearDown(self):
        Activity.objects.all().delete()
        Workspace.objects.all().delete()
        User.objects.all().delete()
