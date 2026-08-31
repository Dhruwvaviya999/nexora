"""
End-to-end smoke walk across every API area.

Exercises the full happy path a real user takes -- register, build a workspace,
invite a teammate, create content, collaborate, hand a task over, read the
dashboards -- so that a regression anywhere in the request/response chain
surfaces here even for apps that have no dedicated test module yet.

Every step records its outcome instead of aborting, so one run reports all
breakages rather than only the first.
"""

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

API = "/api/v1"


class SmokeWalkTests(APITestCase):
    """One long walk through the API, reporting every failing step."""

    maxDiff = None

    def setUp(self):
        self.failures: list[str] = []
        self.owner = APIClient()
        self.member = APIClient()

    # -- helpers ---------------------------------------------------------
    def call(self, client, method, url, data=None, expect=(200, 201, 204), name=""):
        """Perform a request, record (don't raise) unexpected status codes."""
        fn = getattr(client, method.lower())
        if method.upper() in {"GET", "DELETE"}:
            response = fn(url)
        else:
            response = fn(url, data, format="json")
        label = name or f"{method.upper()} {url}"
        if response.status_code not in expect:
            body = getattr(response, "data", None)
            if body is None:
                body = getattr(response, "content", b"")[:300]
            self.failures.append(
                f"{label} -> {response.status_code} (expected {expect}): {body!r}"
            )
        return response

    def auth(self, client, email, password="Str0ng!Passw0rd"):
        response = client.post(
            f"{API}/auth/login/",
            {"email": email, "password": password},
            format="json",
        )
        token = (response.data or {}).get("access")
        if token:
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        else:
            self.failures.append(f"login({email}) -> {response.status_code}: {response.data!r}")
        return token

    # -- the walk --------------------------------------------------------
    def test_full_api_walk(self):
        pwd = "Str0ng!Passw0rd"
        owner_email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
        member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"

        # --- auth --------------------------------------------------------
        self.call(
            self.owner,
            "POST",
            f"{API}/auth/register/",
            {
                "name": "Owner One",
                "email": owner_email,
                "password": pwd,
                "password_confirm": pwd,
            },
            expect=(201,),
            name="register owner",
        )
        self.call(
            self.member,
            "POST",
            f"{API}/auth/register/",
            {
                "name": "Member Two",
                "email": member_email,
                "password": pwd,
                "password_confirm": pwd,
            },
            expect=(201,),
            name="register member",
        )
        self.auth(self.owner, owner_email, pwd)
        self.auth(self.member, member_email, pwd)
        self.call(self.owner, "GET", f"{API}/auth/me/", expect=(200,), name="auth me")
        self.call(self.owner, "GET", f"{API}/health/", expect=(200,), name="health")

        # --- workspace ---------------------------------------------------
        ws_response = self.call(
            self.owner,
            "POST",
            f"{API}/workspaces/",
            {"name": "Smoke Workspace", "description": "created by smoke walk"},
            expect=(201,),
            name="create workspace",
        )
        if ws_response.status_code != 201:
            self.report()
            return
        ws = ws_response.data["id"]

        self.call(self.owner, "GET", f"{API}/workspaces/", expect=(200,), name="list workspaces")
        self.call(
            self.owner, "GET", f"{API}/workspaces/{ws}/members/", expect=(200,), name="list members"
        )

        # --- invitation --------------------------------------------------
        inv = self.call(
            self.owner,
            "POST",
            f"{API}/invitations/",
            {"workspace": ws, "email": member_email, "role": "member"},
            expect=(201,),
            name="create invitation",
        )
        if inv.status_code == 201:
            token = inv.data.get("token")
            self.call(
                self.owner,
                "GET",
                f"{API}/invitations/?workspace={ws}",
                expect=(200,),
                name="list invitations",
            )
            self.call(
                self.member,
                "POST",
                f"{API}/invitations/{token}/accept/",
                {},
                expect=(200, 201),
                name="accept invitation",
            )

        # --- project -----------------------------------------------------
        proj = self.call(
            self.owner,
            "POST",
            f"{API}/projects/",
            {"workspace": ws, "name": "Smoke Project", "description": "smoke"},
            expect=(201,),
            name="create project",
        )
        if proj.status_code != 201:
            self.report()
            return
        pid = proj.data["id"]

        self.call(
            self.owner, "GET", f"{API}/projects/?workspace={ws}", expect=(200,), name="list projects"
        )
        self.call(
            self.owner,
            "PATCH",
            f"{API}/projects/{pid}/",
            {"description": "updated"},
            expect=(200,),
            name="patch project",
        )
        self.call(
            self.owner, "POST", f"{API}/projects/{pid}/archive/", {}, expect=(200,), name="archive project"
        )
        self.call(
            self.owner, "POST", f"{API}/projects/{pid}/restore/", {}, expect=(200,), name="restore project"
        )

        # --- task --------------------------------------------------------
        member_user = User.objects.get(email=member_email)
        task = self.call(
            self.owner,
            "POST",
            f"{API}/tasks/",
            {
                "workspace": ws,
                "project": pid,
                "title": "Smoke Task",
                "description": "smoke",
                "status": "todo",
                "priority": "medium",
                "assignee_id": str(member_user.id),
            },
            expect=(201,),
            name="create task",
        )
        if task.status_code != 201:
            self.report()
            return
        tid = task.data["id"]

        self.call(self.owner, "GET", f"{API}/tasks/?workspace={ws}", expect=(200,), name="list tasks")
        self.call(
            self.owner,
            "GET",
            f"{API}/tasks/?workspace={ws}&status=todo&priority=medium&search=Smoke&ordering=-created_at",
            expect=(200,),
            name="filter tasks",
        )
        self.call(
            self.owner,
            "PATCH",
            f"{API}/tasks/{tid}/",
            {"status": "in_progress"},
            expect=(200,),
            name="patch task",
        )

        # --- document (multipart: the API requires a real file on create) ----
        upload = SimpleUploadedFile(
            "smoke.txt", b"Nexora smoke document body.", content_type="text/plain"
        )
        doc = self.owner.post(
            f"{API}/documents/",
            {"workspace": ws, "title": "Smoke Doc", "file": upload},
            format="multipart",
        )
        if doc.status_code != 201:
            self.failures.append(f"create document -> {doc.status_code}: {doc.data!r}")
        self.call(
            self.owner,
            "GET",
            f"{API}/documents/?workspace={ws}",
            expect=(200,),
            name="list documents",
        )

        # --- comments + mentions -----------------------------------------
        comment = self.call(
            self.owner,
            "POST",
            f"{API}/comments/",
            {
                "workspace": ws,
                "target_type": "task",
                "target_id": tid,
                "content": f"Heads up @{member_email} please review.",
            },
            expect=(201,),
            name="create comment",
        )
        if comment.status_code == 201:
            cid = comment.data["id"]
            self.call(
                self.member,
                "POST",
                f"{API}/comments/{cid}/reply/",
                {"content": "On it."},
                expect=(201,),
                name="reply to comment",
            )
            self.call(
                self.owner,
                "GET",
                f"{API}/comments/?workspace={ws}&target_type=task&target_id={tid}",
                expect=(200,),
                name="list comments",
            )

        self.call(
            self.member,
            "GET",
            f"{API}/mentions/?workspace={ws}",
            expect=(200,),
            name="list mentions",
        )

        # --- notifications -------------------------------------------------
        self.call(
            self.member, "GET", f"{API}/notifications/", expect=(200,), name="list notifications"
        )
        self.call(
            self.member,
            "GET",
            f"{API}/notifications/unread-count/",
            expect=(200,),
            name="unread count",
        )
        self.call(
            self.member,
            "PATCH",
            f"{API}/notifications/read-all/",
            {},
            expect=(200, 204),
            name="mark all read",
        )

        # --- handover --------------------------------------------------------
        handover = self.call(
            self.member,
            "POST",
            f"{API}/handovers/",
            {
                "workspace": ws,
                "task": tid,
                "to_user_id": str(User.objects.get(email=owner_email).id),
                "summary": "Did the first half.",
                "pending_items": "Second half remains.",
                "resources": "See the smoke doc.",
            },
            expect=(201,),
            name="create handover",
        )
        if handover.status_code == 201:
            hid = handover.data["id"]
            self.call(
                self.owner,
                "GET",
                f"{API}/handovers/?workspace={ws}",
                expect=(200,),
                name="list handovers",
            )
            self.call(
                self.owner,
                "POST",
                f"{API}/handovers/{hid}/review/",
                {"decision": "approved", "comment": "Looks good."},
                expect=(200,),
                name="approve handover",
            )
            self.call(
                self.owner,
                "GET",
                f"{API}/handovers/{hid}/export/",
                expect=(200,),
                name="export handover pdf",
            )

        # --- dashboards ------------------------------------------------------
        self.call(
            self.owner, "GET", f"{API}/dashboard/?workspace={ws}", expect=(200,), name="dashboard"
        )
        self.call(
            self.owner, "GET", f"{API}/analytics/?workspace={ws}", expect=(200,), name="analytics"
        )
        self.call(
            self.owner,
            "GET",
            f"{API}/activities/?workspace={ws}",
            expect=(200,),
            name="activity feed",
        )
        self.call(
            self.owner,
            "GET",
            f"{API}/activities/export/?workspace={ws}",
            expect=(200,),
            name="activity csv export",
        )

        # --- ai (metadata endpoints only; no provider calls) -----------------
        self.call(
            self.owner,
            "GET",
            f"{API}/ai/settings/?workspace={ws}",
            expect=(200,),
            name="ai settings",
        )
        self.call(
            self.owner,
            "GET",
            f"{API}/ai/conversations/?workspace={ws}",
            expect=(200,),
            name="ai conversations",
        )
        self.call(
            self.owner,
            "GET",
            f"{API}/ai/prompt-templates/?workspace={ws}",
            expect=(200,),
            name="ai prompt templates",
        )
        self.call(
            self.owner,
            "GET",
            f"{API}/ai/search-history/?workspace={ws}",
            expect=(200,),
            name="ai search history",
        )

        # --- tenancy isolation -------------------------------------------
        outsider = APIClient()
        outsider_email = f"outsider-{uuid.uuid4().hex[:8]}@example.com"
        outsider.post(
            f"{API}/auth/register/",
            {
                "name": "Outsider",
                "email": outsider_email,
                "password": pwd,
                "password_confirm": pwd,
            },
            format="json",
        )
        self.auth(outsider, outsider_email, pwd)
        self.call(
            outsider,
            "GET",
            f"{API}/tasks/{tid}/",
            expect=(403, 404),
            name="outsider blocked from task",
        )
        self.call(
            outsider,
            "GET",
            f"{API}/projects/{pid}/",
            expect=(403, 404),
            name="outsider blocked from project",
        )
        self.call(
            outsider,
            "GET",
            f"{API}/analytics/?workspace={ws}",
            expect=(403, 404),
            name="outsider blocked from analytics",
        )

        # --- unauthenticated access --------------------------------------
        anon = APIClient()
        self.call(anon, "GET", f"{API}/tasks/", expect=(401,), name="anon blocked from tasks")
        self.call(
            anon, "GET", f"{API}/workspaces/", expect=(401,), name="anon blocked from workspaces"
        )

        self.report()

    def report(self):
        if self.failures:
            lines = "\n  ".join(self.failures)
            self.fail(f"{len(self.failures)} API step(s) failed:\n  {lines}")
