"""API tests for dashboard/analytics aggregates and the audit-log export."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()


class AnalyticsAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.outsider = User.objects.create_user("outsider@example.com", "pass12345")
        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        WorkspaceMember.objects.create(
            workspace=self.workspace, user=self.owner, role=WorkspaceRole.OWNER
        )
        self.project = Project.objects.create(
            workspace=self.workspace, name="Site", created_by=self.owner
        )
        Task.objects.create(
            workspace=self.workspace,
            project=self.project,
            title="Open task",
            assignee=self.owner,
            created_by=self.owner,
        )
        Task.objects.create(
            workspace=self.workspace,
            project=self.project,
            title="Done task",
            status=TaskStatus.COMPLETED,
            created_by=self.owner,
        )

    def test_analytics_shape_and_counts(self):
        self.client.force_authenticate(self.owner)
        res = self.client.get(f"/api/v1/analytics/?workspace={self.workspace.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        for key in ("task_status", "task_priority", "weekly", "workload", "handovers"):
            self.assertIn(key, res.data)
        self.assertEqual(len(res.data["weekly"]), 8)
        status_counts = {r["status"]: r["count"] for r in res.data["task_status"]}
        self.assertEqual(status_counts.get("todo"), 1)
        self.assertEqual(status_counts.get("completed"), 1)
        self.assertEqual(res.data["workload"][0]["count"], 1)
        self.assertEqual(res.data["handovers"]["pending"], 0)

    def test_analytics_requires_membership(self):
        self.client.force_authenticate(self.outsider)
        res = self.client.get(f"/api/v1/analytics/?workspace={self.workspace.id}")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_analytics_requires_workspace_param(self):
        self.client.force_authenticate(self.owner)
        res = self.client.get("/api/v1/analytics/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_audit_log_csv_export(self):
        self.client.force_authenticate(self.owner)
        res = self.client.get(
            f"/api/v1/activities/export/?workspace={self.workspace.id}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        body = res.content.decode()
        self.assertIn("timestamp,actor,action", body)
        # Task creations above were logged by the activities signal handlers.
        self.assertIn("task.created", body)
