"""
Document API tests.

Two areas:

* **Upload handling** — metadata capture, and the size/type validation that was
  previously absent (any file of any size was accepted and stored).
* **The download endpoint** — uploads are never exposed at a public /media/
  URL, so the authenticated, workspace-scoped ``download`` action is now the
  only way to read a file. That makes it a tenant boundary and it is tested as
  one.

Embedding is disabled for these tests: ``knowledge`` reacts to Document
creation via a post_save signal, and loading a transformer model has nothing to
do with what is under test here.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document
from apps.knowledge.handlers import ingestion_disabled
from apps.projects.models import Project
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

BASE = "/api/v1/documents/"


def upload(name="notes.txt", content=b"hello world", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class DocumentAPITests(APITestCase):
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

    def _upload(self, file=None, **overrides):
        payload = {"workspace": str(self.workspace.id), "file": file or upload()}
        payload.update(overrides)
        with ingestion_disabled():
            return self.client.post(BASE, payload, format="multipart")

    # -- Upload -------------------------------------------------------------

    def test_upload_captures_metadata(self):
        response = self._upload()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        doc = Document.objects.get(pk=response.data["id"])
        self.assertEqual(doc.uploaded_by, self.owner)
        self.assertEqual(doc.workspace, self.workspace)
        self.assertGreater(doc.file_size, 0)
        self.assertTrue(doc.file_type)

    def test_title_defaults_to_the_filename(self):
        response = self._upload(file=upload(name="runbook.txt"))
        self.assertEqual(response.data["title"], "runbook.txt")

    def test_explicit_title_wins(self):
        response = self._upload(file=upload(name="runbook.txt"), title="Q3 Runbook")
        self.assertEqual(response.data["title"], "Q3 Runbook")

    def test_file_is_required_on_create(self):
        response = self.client.post(
            BASE, {"workspace": str(self.workspace.id), "title": "No file"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_metadata_only_update_needs_no_file(self):
        doc_id = self._upload().data["id"]
        response = self.client.patch(
            f"{BASE}{doc_id}/", {"description": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "Updated")

    def test_stored_path_is_partitioned_by_workspace(self):
        doc_id = self._upload().data["id"]
        doc = Document.objects.get(pk=doc_id)
        self.assertIn(f"documents/{self.workspace.id}/", doc.file.name)

    # -- Upload validation (previously absent) ------------------------------

    def test_oversized_upload_is_rejected(self):
        from django.conf import settings

        too_big = upload(
            name="huge.txt", content=b"x" * (settings.MAX_UPLOAD_SIZE + 1)
        )
        response = self._upload(file=too_big)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertIn("too large", str(response.data["file"]).lower())

    def test_disallowed_extension_is_rejected(self):
        """An .html upload served back would execute on the API's origin."""
        response = self._upload(
            file=upload(name="evil.html", content=b"<script>1</script>",
                        content_type="text/html")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertIn("unsupported file type", str(response.data["file"]).lower())

    def test_executable_extension_is_rejected(self):
        response = self._upload(
            file=upload(name="payload.exe", content=b"MZ",
                        content_type="application/octet-stream")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_allowed_non_text_type_is_accepted(self):
        response = self._upload(
            file=upload(name="diagram.png", content=b"\x89PNG\r\n", content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # -- Download -----------------------------------------------------------

    def test_file_url_points_at_the_authenticated_endpoint(self):
        """Never a raw /media/ path: that would be an unauthenticated read."""
        response = self._upload()
        self.assertIn(f"/documents/{response.data['id']}/download/",
                      response.data["file_url"])
        self.assertNotIn("/media/", response.data["file_url"])

    def test_member_can_download(self):
        doc_id = self._upload().data["id"]
        self.client.force_authenticate(self.member)

        response = self.client.get(f"{BASE}{doc_id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), b"hello world")

    def test_download_forces_an_attachment(self):
        doc_id = self._upload().data["id"]
        response = self.client.get(f"{BASE}{doc_id}/download/")
        self.assertTrue(
            response["Content-Disposition"].startswith("attachment;")
        )
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_outsider_cannot_download(self):
        """The tenant boundary applies to file bytes, not just JSON."""
        doc_id = self._upload().data["id"]
        self.client.force_authenticate(self.outsider)

        response = self.client.get(f"{BASE}{doc_id}/download/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_download(self):
        doc_id = self._upload().data["id"]
        self.client.force_authenticate(None)

        response = self.client.get(f"{BASE}{doc_id}/download/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Scoping ------------------------------------------------------------

    def test_list_is_scoped_to_my_workspaces(self):
        self._upload()
        self.client.force_authenticate(self.outsider)
        response = self.client.get(BASE)
        self.assertEqual(response.data["count"], 0)

    def test_project_filter(self):
        self._upload(title="Loose")
        self._upload(title="In project", project=str(self.project.id))

        response = self.client.get(BASE, {"project": str(self.project.id)})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["In project"])
