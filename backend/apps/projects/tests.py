"""
Project API tests.

Covers the two things that are project-specific rather than inherited from
``WorkspaceScopedViewSet``: the archive/restore actions, and per-workspace slug
uniqueness (slugs are unique within a tenant, not globally — unlike workspace
slugs).
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.projects.models import Project, ProjectStatus
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

BASE = "/api/v1/projects/"


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.member = User.objects.create_user("member@example.com", "pass12345")

        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.member, WorkspaceRole.MEMBER),
        ):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=user, role=role
            )
        self.client.force_authenticate(self.owner)

    def _create(self, **overrides):
        payload = {
            "workspace": str(self.workspace.id),
            "name": "Website revamp",
            **overrides,
        }
        return self.client.post(BASE, payload, format="json")

    # -- Creation defaults --------------------------------------------------

    def test_creator_owns_the_project_by_default(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner"]["id"], str(self.owner.id))

    def test_defaults(self):
        response = self._create()
        self.assertEqual(response.data["status"], ProjectStatus.PLANNING)
        self.assertFalse(response.data["archived"])
        self.assertTrue(response.data["slug"])

    # -- Slug generation ----------------------------------------------------

    def test_slug_is_generated_from_the_name(self):
        response = self._create(name="Website Revamp")
        self.assertEqual(response.data["slug"], "website-revamp")

    def test_duplicate_names_get_suffixed_slugs_within_a_workspace(self):
        first = self._create(name="Same Name")
        second = self._create(name="Same Name")
        self.assertEqual(first.data["slug"], "same-name")
        self.assertEqual(second.data["slug"], "same-name-2")

    def test_slugs_are_unique_per_workspace_not_globally(self):
        """Two tenants may both have a 'website-revamp' project."""
        other_owner = User.objects.create_user("other@example.com", "pass12345")
        other_ws = Workspace.objects.create(name="Other", owner=other_owner)
        WorkspaceMember.objects.create(
            workspace=other_ws, user=other_owner, role=WorkspaceRole.OWNER
        )

        mine = self._create(name="Website Revamp")

        self.client.force_authenticate(other_owner)
        theirs = self.client.post(
            BASE,
            {"workspace": str(other_ws.id), "name": "Website Revamp"},
            format="json",
        )
        self.assertEqual(theirs.status_code, status.HTTP_201_CREATED)
        # Same slug, different workspaces — allowed.
        self.assertEqual(mine.data["slug"], theirs.data["slug"])

    def test_unsluggable_name_falls_back(self):
        response = self._create(name="日本語")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["slug"])

    # -- Archive / restore --------------------------------------------------

    def test_archive_sets_the_flag_and_stamps_updated_by(self):
        project_id = self._create().data["id"]
        self.client.force_authenticate(self.member)

        response = self.client.post(f"{BASE}{project_id}/archive/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["archived"])

        project = Project.objects.get(pk=project_id)
        self.assertEqual(project.updated_by, self.member)

    def test_restore_clears_the_flag(self):
        project_id = self._create().data["id"]
        self.client.post(f"{BASE}{project_id}/archive/")

        response = self.client.post(f"{BASE}{project_id}/restore/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["archived"])

    def test_archived_is_independent_of_status(self):
        """A project can be completed but not archived, and vice versa."""
        project_id = self._create(status=ProjectStatus.COMPLETED).data["id"]
        project = Project.objects.get(pk=project_id)
        self.assertEqual(project.status, ProjectStatus.COMPLETED)
        self.assertFalse(project.archived)

    def test_archive_requires_membership(self):
        project_id = self._create().data["id"]
        outsider = User.objects.create_user("out@example.com", "pass12345")
        self.client.force_authenticate(outsider)

        response = self.client.post(f"{BASE}{project_id}/archive/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Filtering ----------------------------------------------------------

    def test_archived_filter(self):
        keep = self._create(name="Active one").data["id"]
        drop = self._create(name="Archived one").data["id"]
        self.client.post(f"{BASE}{drop}/archive/")

        response = self.client.get(BASE, {"archived": "false"})
        ids = [row["id"] for row in response.data["results"]]
        self.assertIn(keep, ids)
        self.assertNotIn(drop, ids)

    def test_status_filter(self):
        self._create(name="Planned")
        self._create(name="Running", status=ProjectStatus.ACTIVE)

        response = self.client.get(BASE, {"status": ProjectStatus.ACTIVE})
        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["Running"])
