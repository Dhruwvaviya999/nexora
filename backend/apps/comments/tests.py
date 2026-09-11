"""
Comment API tests.

Covers the parts that are easy to get subtly wrong: the target whitelist, reply
target inheritance, soft delete, and the author-vs-admin permission split.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.comments.models import Comment
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

BASE = "/api/v1/comments/"


class CommentAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass12345")
        self.admin = User.objects.create_user("admin@example.com", "pass12345")
        self.author = User.objects.create_user("author@example.com", "pass12345")
        self.other = User.objects.create_user("other@example.com", "pass12345")
        self.outsider = User.objects.create_user("outsider@example.com", "pass12345")

        self.workspace = Workspace.objects.create(name="Acme", owner=self.owner)
        for user, role in (
            (self.owner, WorkspaceRole.OWNER),
            (self.admin, WorkspaceRole.ADMIN),
            (self.author, WorkspaceRole.MEMBER),
            (self.other, WorkspaceRole.MEMBER),
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
            title="Ship it",
            created_by=self.owner,
        )

    def _post(self, user=None, **overrides):
        self.client.force_authenticate(user or self.author)
        payload = {
            "target_type": "task",
            "target_id": str(self.task.id),
            "content": "Looks good to me.",
            **overrides,
        }
        return self.client.post(BASE, payload, format="json")

    # -- Creation -----------------------------------------------------------

    def test_member_can_comment_on_a_task(self):
        response = self._post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(comment.author, self.author)
        # Workspace is resolved from the target, never sent by the client.
        self.assertEqual(comment.workspace, self.workspace)

    def test_outsider_cannot_comment(self):
        response = self._post(user=self.outsider)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_content_is_rejected(self):
        response = self._post(content="   ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_target_type_and_id_are_required(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(BASE, {"content": "Orphan"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_target_type_outside_the_whitelist_is_rejected(self):
        """Only project/task/document accept comments."""
        response = self._post(target_type="user")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_comment_on_a_project(self):
        response = self._post(target_type="project", target_id=str(self.project.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # -- Threading ----------------------------------------------------------

    def test_reply_inherits_the_parents_target(self):
        parent_id = self._post().data["id"]
        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"{BASE}{parent_id}/reply/", {"content": "Agreed."}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        parent = Comment.objects.get(pk=parent_id)
        reply = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(reply.parent_id, parent.pk)
        self.assertEqual(reply.content_type_id, parent.content_type_id)
        self.assertEqual(reply.object_id, parent.object_id)

    def test_cannot_reply_to_a_deleted_comment(self):
        parent_id = self._post().data["id"]
        self.client.delete(f"{BASE}{parent_id}/")

        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"{BASE}{parent_id}/reply/", {"content": "Too late"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Editing ------------------------------------------------------------

    def test_author_can_edit_and_it_is_marked_edited(self):
        comment_id = self._post().data["id"]
        response = self.client.patch(
            f"{BASE}{comment_id}/", {"content": "Revised."}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_edited"])

    def test_another_member_cannot_edit_my_comment(self):
        comment_id = self._post().data["id"]
        self.client.force_authenticate(self.other)
        response = self.client.patch(
            f"{BASE}{comment_id}/", {"content": "Hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_edit_someone_elses_comment(self):
        """Moderation covers deletion, not rewriting what someone said."""
        comment_id = self._post().data["id"]
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"{BASE}{comment_id}/", {"content": "Reworded"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- Deletion -----------------------------------------------------------

    def test_delete_is_soft_and_blanks_the_content(self):
        comment_id = self._post().data["id"]
        response = self.client.delete(f"{BASE}{comment_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        comment = Comment.objects.get(pk=comment_id)
        self.assertTrue(comment.is_deleted)
        # Genuinely erased, not merely hidden by the serializer.
        self.assertEqual(comment.content, "")

    def test_deleted_comment_renders_as_placeholder(self):
        comment_id = self._post().data["id"]
        self.client.delete(f"{BASE}{comment_id}/")

        response = self.client.get(
            BASE, {"target_type": "task", "target_id": str(self.task.id)}
        )
        row = next(r for r in response.data["results"] if r["id"] == comment_id)
        self.assertEqual(row["content"], "[deleted]")

    def test_admin_can_delete_someone_elses_comment(self):
        comment_id = self._post().data["id"]
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"{BASE}{comment_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_plain_member_cannot_delete_someone_elses_comment(self):
        comment_id = self._post().data["id"]
        self.client.force_authenticate(self.other)
        response = self.client.delete(f"{BASE}{comment_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- Listing ------------------------------------------------------------

    def test_list_is_filtered_by_target(self):
        self._post()
        self._post(target_type="project", target_id=str(self.project.id))

        response = self.client.get(
            BASE, {"target_type": "task", "target_id": str(self.task.id)}
        )
        self.assertEqual(response.data["count"], 1)

    def test_list_is_scoped_to_my_workspaces(self):
        self._post()
        self.client.force_authenticate(self.outsider)
        response = self.client.get(BASE)
        self.assertEqual(response.data["count"], 0)

    def test_threads_read_oldest_first(self):
        first = self._post(content="First").data["id"]
        second = self._post(content="Second").data["id"]

        response = self.client.get(
            BASE, {"target_type": "task", "target_id": str(self.task.id)}
        )
        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, [first, second])
