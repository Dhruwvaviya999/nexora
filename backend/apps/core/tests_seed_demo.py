"""
Tests for the ``seed_demo`` management command.

The command is what fills a fresh install with demo content, so a failure here
means the first thing a reviewer runs is broken. Embedding is skipped: the
vector pass downloads and runs a local transformer model, which is far too slow
for a test run and is not what these tests are checking.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.activities.models import Activity
from apps.comments.models import Comment
from apps.documents.models import Document
from apps.handovers.models import Handover
from apps.invitations.models import Invitation
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember

User = get_user_model()

OWNER = "seed.owner@example.com"


class SeedDemoCommandTests(TestCase):
    """The command must run clean, be idempotent under --reset, and be scoped."""

    def seed(self, *extra):
        out, err = StringIO(), StringIO()
        call_command(
            "seed_demo",
            "--skip-embedding",
            "--owner-email",
            OWNER,
            *extra,
            stdout=out,
            stderr=err,
        )
        return out.getvalue(), err.getvalue()

    def test_seed_creates_content_across_every_app(self):
        self.seed()

        self.assertEqual(Workspace.objects.count(), 3)
        owner = User.objects.get(email=OWNER)
        for model in (Project, Task, Document, Handover, Comment, Notification, Invitation):
            self.assertGreater(
                model.objects.count(), 0, f"{model.__name__} was not seeded"
            )
        self.assertGreater(Activity.objects.count(), 0, "activity trail was not seeded")
        self.assertTrue(
            WorkspaceMember.objects.filter(user=owner).exists(),
            "the owner account was not added to any workspace",
        )

    def test_seed_covers_every_enum_value(self):
        """Filters and charts need at least one row per enum value."""
        self.seed()

        for field, model in (("status", Task), ("priority", Task), ("status", Handover)):
            choices = {c[0] for c in model._meta.get_field(field).choices}
            seeded = set(model.objects.values_list(field, flat=True))
            self.assertEqual(
                choices - seeded,
                set(),
                f"{model.__name__}.{field} is missing values: {choices - seeded}",
            )

    def test_reset_is_idempotent(self):
        self.seed()
        first = (Workspace.objects.count(), Task.objects.count())

        self.seed("--reset")
        second = (Workspace.objects.count(), Task.objects.count())

        self.assertEqual(first, second, "--reset did not produce an identical dataset")

    def test_reset_leaves_real_accounts_and_their_data_alone(self):
        keeper = User.objects.create_user(
            email="real.person@example.com", password="Str0ng!Passw0rd", name="Real Person"
        )
        keeper_ws = Workspace.objects.create(name="Real Workspace", owner=keeper)

        self.seed()
        self.seed("--reset")

        self.assertTrue(User.objects.filter(pk=keeper.pk).exists(), "a real account was deleted")
        self.assertTrue(
            Workspace.objects.filter(pk=keeper_ws.pk).exists(),
            "a real workspace was deleted",
        )

    def test_same_seed_produces_the_same_dataset(self):
        self.seed("--seed", "1234")
        titles_first = sorted(Task.objects.values_list("title", flat=True))

        self.seed("--reset", "--seed", "1234")
        titles_second = sorted(Task.objects.values_list("title", flat=True))

        self.assertEqual(titles_first, titles_second, "the RNG seed is not deterministic")
