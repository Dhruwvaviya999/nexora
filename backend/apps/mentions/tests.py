"""
Mention tests.

The mention sync is the subtlest piece of logic in the collaboration stack: it
runs on *every* comment save and must be idempotent, or editing a comment would
re-notify everyone in it. It also enforces two rules that only exist here —
mentions are limited to workspace members, and you cannot mention yourself.

The token format ``@[Display Name](<uuid>)`` is a contract with
``components/comments/mention-textarea.tsx`` that nothing type-checks, so it is
pinned here.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.comments.models import Comment
from apps.mentions.models import Mention
from apps.mentions.services import extract_mentioned_ids, sync_comment_mentions
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()


def token(user) -> str:
    """The exact token shape the frontend autocomplete emits."""
    return f"@[{user.name or user.email}]({user.id})"


class MentionParsingTests(TestCase):
    def test_extracts_a_single_uuid(self):
        uid = "3f2c1b4a-5d6e-4f70-8a91-b2c3d4e5f607"
        self.assertEqual(
            extract_mentioned_ids(f"hey @[Asha Rao]({uid}) look"), {uid}
        )

    def test_extracts_several(self):
        a = "3f2c1b4a-5d6e-4f70-8a91-b2c3d4e5f607"
        b = "11111111-2222-3333-4444-555555555555"
        text = f"@[A]({a}) and @[B]({b})"
        self.assertEqual(extract_mentioned_ids(text), {a, b})

    def test_ignores_malformed_tokens(self):
        self.assertEqual(extract_mentioned_ids("@[Asha](not-a-uuid)"), set())
        self.assertEqual(extract_mentioned_ids("@Asha"), set())
        self.assertEqual(extract_mentioned_ids("plain text"), set())

    def test_handles_empty_input(self):
        self.assertEqual(extract_mentioned_ids(""), set())
        self.assertEqual(extract_mentioned_ids(None), set())


class MentionSyncTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            "author@example.com", "pass12345", name="Author"
        )
        self.alice = User.objects.create_user(
            "alice@example.com", "pass12345", name="Alice"
        )
        self.bob = User.objects.create_user("bob@example.com", "pass12345", name="Bob")
        self.outsider = User.objects.create_user(
            "out@example.com", "pass12345", name="Outsider"
        )

        self.workspace = Workspace.objects.create(name="Acme", owner=self.author)
        for user in (self.author, self.alice, self.bob):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=user, role=WorkspaceRole.MEMBER
            )

        self.project = Project.objects.create(
            workspace=self.workspace, name="Site", created_by=self.author
        )
        self.task = Task.objects.create(
            workspace=self.workspace,
            project=self.project,
            title="Ship it",
            created_by=self.author,
        )
        self.task_ct = ContentType.objects.get_for_model(Task)

    def _comment(self, content: str) -> Comment:
        """Create a comment. The post_save signal runs the sync for us."""
        return Comment.objects.create(
            workspace=self.workspace,
            author=self.author,
            content=content,
            content_type=self.task_ct,
            object_id=self.task.id,
        )

    # -- Basic behaviour ----------------------------------------------------

    def test_mentioning_a_member_creates_a_mention_and_a_notification(self):
        comment = self._comment(f"ping {token(self.alice)}")

        self.assertTrue(
            Mention.objects.filter(comment=comment, mentioned_user=self.alice).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.alice, type=NotificationType.MENTION
            ).exists()
        )

    def test_mentioning_a_non_member_is_ignored(self):
        comment = self._comment(f"ping {token(self.outsider)}")
        self.assertEqual(comment.mentions.count(), 0)
        self.assertFalse(Notification.objects.filter(recipient=self.outsider).exists())

    def test_cannot_mention_yourself(self):
        comment = self._comment(f"note to self {token(self.author)}")
        self.assertEqual(comment.mentions.count(), 0)
        self.assertFalse(Notification.objects.filter(recipient=self.author).exists())

    def test_duplicate_mentions_in_one_comment_collapse(self):
        comment = self._comment(f"{token(self.alice)} and again {token(self.alice)}")
        self.assertEqual(
            Mention.objects.filter(comment=comment, mentioned_user=self.alice).count(),
            1,
        )

    def test_workspace_is_denormalised_onto_the_mention(self):
        comment = self._comment(f"ping {token(self.alice)}")
        mention = Mention.objects.get(comment=comment)
        self.assertEqual(mention.workspace, self.workspace)

    # -- Idempotency (the important part) -----------------------------------

    def test_resaving_unchanged_content_does_not_renotify(self):
        comment = self._comment(f"ping {token(self.alice)}")
        self.assertEqual(Notification.objects.filter(recipient=self.alice).count(), 1)

        comment.save()  # fires post_save -> sync again
        sync_comment_mentions(comment)  # and explicitly, for good measure

        self.assertEqual(comment.mentions.count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.alice).count(), 1)

    def test_editing_to_add_a_mention_notifies_only_the_new_person(self):
        comment = self._comment(f"ping {token(self.alice)}")

        comment.content = f"ping {token(self.alice)} and {token(self.bob)}"
        comment.save()

        self.assertEqual(comment.mentions.count(), 2)
        # Alice was not notified a second time.
        self.assertEqual(Notification.objects.filter(recipient=self.alice).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.bob).count(), 1)

    def test_editing_to_remove_a_mention_deletes_the_row(self):
        comment = self._comment(f"{token(self.alice)} {token(self.bob)}")
        self.assertEqual(comment.mentions.count(), 2)

        comment.content = f"only {token(self.alice)} now"
        comment.save()

        remaining = list(comment.mentions.values_list("mentioned_user_id", flat=True))
        self.assertEqual(remaining, [self.alice.id])

    def test_soft_deleting_a_comment_clears_its_mentions(self):
        """Delete blanks the content, so the next sync finds no tokens."""
        comment = self._comment(f"ping {token(self.alice)}")
        self.assertEqual(comment.mentions.count(), 1)

        comment.is_deleted = True
        comment.content = ""
        comment.save()

        self.assertEqual(comment.mentions.count(), 0)
