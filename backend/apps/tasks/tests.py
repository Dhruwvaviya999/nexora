"""
Task API tests.

Focused on the rules that live in ``TaskSerializer.validate`` — the workspace
derivation and the membership checks on assignee/reporter. Those are the
correctness guarantees that stop a client placing a task in the wrong tenant or
assigning it to someone outside the workspace, and neither had a direct test.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.projects.models import Project
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

BASE = "/api/v1/tasks/"


class TaskAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.member = User.objects.create_user("member@example.com", "pass12345")
        self.outsider = User.objects.create_user("outsider@example.com", "pass12345")

        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.member, WorkspaceRole.MEMBER),
        ):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=user, role=role
            )

        self.project = Project.objects.create(
            workspace=self.workspace, name="Site", created_by=self.owner
        )
        self.client.force_authenticate(self.owner)

    def _create(self, **overrides):
        payload = {"project": str(self.project.id), "title": "Task", **overrides}
        return self.client.post(BASE, payload, format="json")

    # -- Workspace derivation ----------------------------------------------

    def test_workspace_is_derived_from_the_project(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.workspace, self.workspace)

    def test_client_supplied_workspace_is_ignored(self):
        """``workspace`` is read-only, so a mismatched value cannot take effect."""
        other_owner = User.objects.create_user("other@example.com", "pass12345")
        other_ws = Workspace.objects.create(name="Other", owner=other_owner)
        WorkspaceMember.objects.create(
            workspace=other_ws, user=other_owner, role=WorkspaceRole.OWNER
        )

        response = self._create(workspace=str(other_ws.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        # Derived from the project, not from what the client sent.
        self.assertEqual(task.workspace, self.workspace)

    def test_project_is_required(self):
        response = self.client.post(BASE, {"title": "No project"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", response.data)

    # -- Membership checks on relations ------------------------------------

    def test_assignee_must_be_a_workspace_member(self):
        response = self._create(assignee_id=str(self.outsider.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assignee_id", response.data)

    def test_assignee_that_is_a_member_is_accepted(self):
        response = self._create(assignee_id=str(self.member.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["assignee"]["id"], str(self.member.id))

    def test_reporter_must_be_a_workspace_member(self):
        response = self._create(reporter_id=str(self.outsider.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reporter_id", response.data)

    def test_reporter_defaults_to_the_creating_user(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.reporter, self.owner)

    def test_membership_is_rechecked_on_update(self):
        created = self._create()
        task_id = created.data["id"]
        response = self.client.patch(
            f"{BASE}{task_id}/", {"assignee_id": str(self.outsider.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assignee_can_be_cleared(self):
        created = self._create(assignee_id=str(self.member.id))
        task_id = created.data["id"]
        response = self.client.patch(
            f"{BASE}{task_id}/", {"assignee_id": None}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["assignee"])

    # -- Defaults and enums -------------------------------------------------

    def test_defaults_are_applied(self):
        response = self._create()
        self.assertEqual(response.data["status"], TaskStatus.TODO)
        self.assertEqual(response.data["priority"], TaskPriority.MEDIUM)
        self.assertEqual(response.data["labels"], [])

    def test_invalid_status_is_rejected(self):
        response = self._create(status="banana")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    # -- Filtering ----------------------------------------------------------

    def test_status_filter_narrows_the_list(self):
        self._create(title="Open one")
        done = self._create(title="Done one")
        self.client.patch(
            f"{BASE}{done.data['id']}/",
            {"status": TaskStatus.COMPLETED},
            format="json",
        )

        response = self.client.get(BASE, {"status": TaskStatus.COMPLETED})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Done one"])

    def test_due_date_range_filters(self):
        self._create(title="Early", due_date="2026-01-10")
        self._create(title="Late", due_date="2026-06-10")

        response = self.client.get(BASE, {"due_before": "2026-03-01"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Early"])

        response = self.client.get(BASE, {"due_after": "2026-03-01"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Late"])

    def test_search_matches_title_and_description(self):
        self._create(title="Refactor billing", description="")
        self._create(title="Unrelated", description="mentions billing here")
        self._create(title="Nothing relevant", description="")

        response = self.client.get(BASE, {"search": "billing"})
        self.assertEqual(response.data["count"], 2)

    # -- Cascade ------------------------------------------------------------

    def test_deleting_a_project_deletes_its_tasks(self):
        self._create(title="Doomed")
        self.assertTrue(Task.objects.filter(title="Doomed").exists())
        self.project.delete()
        self.assertFalse(Task.objects.filter(title="Doomed").exists())
