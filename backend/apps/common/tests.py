"""
Tests for the shared foundation in ``apps.common``.

This is the highest-value test file in the project: ``WorkspaceScopedViewSet``
is the single mechanism enforcing multi-tenancy, and every scoped resource
inherits it. A regression here would silently leak data across tenants on every
endpoint at once, which no per-app test would necessarily catch.

Covers:
  * read isolation (404, not 403, for another tenant's row)
  * write isolation (create into a foreign workspace is refused)
  * audit stamping (created_by / updated_by)
  * the permission classes' role matrix
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.permissions import (
    IsWorkspaceAdmin,
    IsWorkspaceAdminOrReadOnly,
    IsWorkspaceManager,
    IsWorkspaceMember,
    IsWorkspaceOwner,
)
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()


class WorkspaceScopedViewSetTests(APITestCase):
    """Tenant isolation, exercised through a real scoped endpoint."""

    def setUp(self):
        self.alice = User.objects.create_user("alice@example.com", "pass12345")
        self.bob = User.objects.create_user("bob@example.com", "pass12345")

        # Two entirely separate tenants.
        self.ws_a = Workspace.objects.create(name="Alpha", owner=self.alice)
        WorkspaceMember.objects.create(
            workspace=self.ws_a, user=self.alice, role=WorkspaceRole.OWNER
        )
        self.ws_b = Workspace.objects.create(name="Beta", owner=self.bob)
        WorkspaceMember.objects.create(
            workspace=self.ws_b, user=self.bob, role=WorkspaceRole.OWNER
        )

        self.project_a = Project.objects.create(
            workspace=self.ws_a, name="Alpha project", created_by=self.alice
        )
        self.project_b = Project.objects.create(
            workspace=self.ws_b, name="Beta project", created_by=self.bob
        )
        self.task_a = Task.objects.create(
            workspace=self.ws_a,
            project=self.project_a,
            title="Alpha task",
            created_by=self.alice,
        )
        self.task_b = Task.objects.create(
            workspace=self.ws_b,
            project=self.project_b,
            title="Beta task",
            created_by=self.bob,
        )

    # -- Read isolation -----------------------------------------------------

    def test_list_returns_only_my_workspaces_rows(self):
        self.client.force_authenticate(self.alice)
        response = self.client.get("/api/v1/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Alpha task"])

    def test_detail_of_another_tenant_returns_404_not_403(self):
        """404 is deliberate: 403 would confirm the id exists."""
        self.client.force_authenticate(self.alice)
        response = self.client.get(f"/api/v1/tasks/{self.task_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_of_another_tenant_returns_404(self):
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            f"/api/v1/tasks/{self.task_b.id}/", {"title": "hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.task_b.refresh_from_db()
        self.assertEqual(self.task_b.title, "Beta task")

    def test_delete_of_another_tenant_returns_404(self):
        self.client.force_authenticate(self.alice)
        response = self.client.delete(f"/api/v1/tasks/{self.task_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(pk=self.task_b.pk).exists())

    def test_anonymous_access_is_rejected(self):
        response = self.client.get("/api/v1/tasks/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Write isolation ----------------------------------------------------

    def test_cannot_create_into_a_workspace_i_am_not_in(self):
        """``get_queryset`` does not run on create; ``_require_membership`` does."""
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/v1/tasks/",
            {"project": str(self.project_b.id), "title": "Injected"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN),
        )
        self.assertFalse(Task.objects.filter(title="Injected").exists())

    def test_membership_is_required_even_with_a_valid_foreign_project_id(self):
        """The workspace is derived from the project, so it cannot be spoofed."""
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/v1/tasks/",
            {
                "project": str(self.project_b.id),
                "workspace": str(self.ws_a.id),  # read-only; must be ignored
                "title": "Spoofed",
            },
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(Task.objects.filter(title="Spoofed").exists())

    # -- Audit stamping -----------------------------------------------------

    def test_create_stamps_created_by_and_updated_by(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/v1/tasks/",
            {"project": str(self.project_a.id), "title": "Stamped"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(title="Stamped")
        self.assertEqual(task.created_by, self.alice)
        self.assertEqual(task.updated_by, self.alice)
        # And the workspace was derived from the project, not supplied.
        self.assertEqual(task.workspace, self.ws_a)

    def test_update_stamps_updated_by_without_touching_created_by(self):
        editor = User.objects.create_user("editor@example.com", "pass12345")
        WorkspaceMember.objects.create(
            workspace=self.ws_a, user=editor, role=WorkspaceRole.MEMBER
        )
        self.client.force_authenticate(editor)
        response = self.client.patch(
            f"/api/v1/tasks/{self.task_a.id}/", {"title": "Edited"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.updated_by, editor)
        self.assertEqual(self.task_a.created_by, self.alice)


class PermissionClassTests(APITestCase):
    """The role matrix, exercised directly against the permission classes."""

    def setUp(self):
        self.owner = User.objects.create_user("o@example.com", "pass12345")
        self.admin = User.objects.create_user("a@example.com", "pass12345")
        self.manager = User.objects.create_user("m@example.com", "pass12345")
        self.member = User.objects.create_user("me@example.com", "pass12345")
        self.outsider = User.objects.create_user("out@example.com", "pass12345")

        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.admin, WorkspaceRole.ADMIN),
            (self.manager, WorkspaceRole.MANAGER),
            (self.member, WorkspaceRole.MEMBER),
        ):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=user, role=role
            )

        self.project = Project.objects.create(
            workspace=self.workspace, name="P", created_by=self.owner
        )

    def _check(self, permission, user, obj, method="GET"):
        request = type("Req", (), {"user": user, "method": method})()
        return permission().has_object_permission(request, None, obj)

    def test_is_workspace_member(self):
        perm = IsWorkspaceMember
        for user in (self.owner, self.admin, self.manager, self.member):
            self.assertTrue(self._check(perm, user, self.workspace))
        self.assertFalse(self._check(perm, self.outsider, self.workspace))

    def test_is_workspace_admin(self):
        perm = IsWorkspaceAdmin
        self.assertTrue(self._check(perm, self.owner, self.workspace))
        self.assertTrue(self._check(perm, self.admin, self.workspace))
        self.assertFalse(self._check(perm, self.manager, self.workspace))
        self.assertFalse(self._check(perm, self.member, self.workspace))

    def test_is_workspace_manager_covers_reviewer_roles(self):
        perm = IsWorkspaceManager
        self.assertTrue(self._check(perm, self.owner, self.workspace))
        self.assertTrue(self._check(perm, self.admin, self.workspace))
        self.assertTrue(self._check(perm, self.manager, self.workspace))
        self.assertFalse(self._check(perm, self.member, self.workspace))

    def test_is_workspace_owner(self):
        perm = IsWorkspaceOwner
        self.assertTrue(self._check(perm, self.owner, self.workspace))
        for user in (self.admin, self.manager, self.member):
            self.assertFalse(self._check(perm, user, self.workspace))

    def test_admin_or_read_only(self):
        perm = IsWorkspaceAdminOrReadOnly
        # Members may read.
        self.assertTrue(self._check(perm, self.member, self.workspace, "GET"))
        # Only owner/admin may write.
        self.assertFalse(self._check(perm, self.member, self.workspace, "PATCH"))
        self.assertTrue(self._check(perm, self.admin, self.workspace, "PATCH"))
        self.assertFalse(self._check(perm, self.outsider, self.workspace, "GET"))

    def test_permissions_resolve_the_workspace_from_a_nested_object(self):
        """One class protects both a workspace and anything hanging off it."""
        self.assertTrue(self._check(IsWorkspaceMember, self.member, self.project))
        self.assertFalse(self._check(IsWorkspaceMember, self.outsider, self.project))


class MaintenanceTaskTests(TestCase):
    """
    The periodic tasks wired into CELERY_BEAT_SCHEDULE.

    Nothing was pruning these tables before: the JWT outstanding-token table in
    particular gains a row per refresh and is read on every token validation.
    Each task must be idempotent, since a beat tick can be delivered twice.
    """

    def setUp(self):
        self.user = User.objects.create_user("maint@example.com", "pass12345")
        self.workspace = Workspace.objects.create(name="Acme", owner=self.user)
        WorkspaceMember.objects.create(
            workspace=self.workspace, user=self.user, role=WorkspaceRole.OWNER
        )

    # -- Expired JWTs -------------------------------------------------------

    def test_flush_expired_tokens_runs_and_removes_expired_rows(self):
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        from apps.common.tasks import flush_expired_tokens

        OutstandingToken.objects.create(
            user=self.user,
            jti="expired-jti",
            token="dummy",
            created_at=timezone.now() - timedelta(days=30),
            expires_at=timezone.now() - timedelta(days=1),
        )
        live_jti = "live-jti"
        OutstandingToken.objects.create(
            user=self.user,
            jti=live_jti,
            token="dummy2",
            created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=1),
        )

        flush_expired_tokens()

        remaining = list(OutstandingToken.objects.values_list("jti", flat=True))
        self.assertEqual(remaining, [live_jti])

    # -- Stale invitations --------------------------------------------------

    def test_expire_stale_invitations_flips_only_past_due_pending_rows(self):
        from apps.common.tasks import expire_stale_invitations
        from apps.invitations.models import Invitation, InvitationStatus

        stale = Invitation.objects.create(
            workspace=self.workspace,
            email="stale@example.com",
            invited_by=self.user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        fresh = Invitation.objects.create(
            workspace=self.workspace,
            email="fresh@example.com",
            invited_by=self.user,
            expires_at=timezone.now() + timedelta(days=1),
        )
        accepted = Invitation.objects.create(
            workspace=self.workspace,
            email="done@example.com",
            invited_by=self.user,
            status=InvitationStatus.ACCEPTED,
            expires_at=timezone.now() - timedelta(days=5),
        )

        updated = expire_stale_invitations()

        self.assertEqual(updated, 1)
        stale.refresh_from_db(); fresh.refresh_from_db(); accepted.refresh_from_db()
        self.assertEqual(stale.status, InvitationStatus.EXPIRED)
        self.assertEqual(fresh.status, InvitationStatus.PENDING)
        # An already-accepted invite is history; it must not be rewritten.
        self.assertEqual(accepted.status, InvitationStatus.ACCEPTED)

    def test_expire_stale_invitations_is_idempotent(self):
        from apps.common.tasks import expire_stale_invitations
        from apps.invitations.models import Invitation

        Invitation.objects.create(
            workspace=self.workspace,
            email="stale@example.com",
            invited_by=self.user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(expire_stale_invitations(), 1)
        self.assertEqual(expire_stale_invitations(), 0)

    # -- Retention ----------------------------------------------------------

    def test_prune_embedding_jobs_keeps_recent_and_unfinished_work(self):
        from apps.common.tasks import prune_embedding_jobs
        from apps.documents.models import Document
        from apps.knowledge.models import EmbeddingJob, EmbeddingStatus

        document = Document.objects.create(
            workspace=self.workspace, title="Doc", file="documents/x/doc.txt"
        )
        old_done = EmbeddingJob.objects.create(
            workspace=self.workspace, document=document,
            status=EmbeddingStatus.COMPLETED,
        )
        old_stuck = EmbeddingJob.objects.create(
            workspace=self.workspace, document=document,
            status=EmbeddingStatus.PROCESSING,
        )
        recent = EmbeddingJob.objects.create(
            workspace=self.workspace, document=document,
            status=EmbeddingStatus.COMPLETED,
        )
        # created_at is auto_now_add, so backdate explicitly.
        cutoff = timezone.now() - timedelta(days=60)
        EmbeddingJob.objects.filter(pk__in=[old_done.pk, old_stuck.pk]).update(
            created_at=cutoff
        )

        deleted = prune_embedding_jobs(days=30)

        self.assertEqual(deleted, 1)
        surviving = set(EmbeddingJob.objects.values_list("pk", flat=True))
        self.assertEqual(surviving, {old_stuck.pk, recent.pk})

    def test_prune_search_history_respects_the_window(self):
        from apps.ai.models import SearchHistory
        from apps.common.tasks import prune_search_history

        old = SearchHistory.objects.create(
            workspace=self.workspace, user=self.user, query="old query"
        )
        recent = SearchHistory.objects.create(
            workspace=self.workspace, user=self.user, query="recent query"
        )
        SearchHistory.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=200)
        )

        deleted = prune_search_history(days=90)

        self.assertEqual(deleted, 1)
        self.assertEqual(
            list(SearchHistory.objects.values_list("pk", flat=True)), [recent.pk]
        )

    # -- Wiring -------------------------------------------------------------

    def test_every_scheduled_task_name_actually_resolves(self):
        """A typo in CELERY_BEAT_SCHEDULE would fail silently at run time."""
        from django.conf import settings

        from config.celery import app

        for entry in settings.CELERY_BEAT_SCHEDULE.values():
            self.assertIn(
                entry["task"],
                app.tasks,
                f"scheduled task {entry['task']!r} is not registered",
            )
