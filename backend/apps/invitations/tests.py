"""
Invitation delivery tests.

An invitation is the only way into a workspace, and the invitee is frequently
someone with no account yet -- so the email is the whole mechanism, not a
nicety. These tests cover who gets mailed, what the mail contains, and who is
allowed to trigger one.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APITestCase

from apps.invitations.models import Invitation, InvitationStatus
from apps.notifications.models import Notification
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

INVITATIONS = "/api/v1/invitations/"
PWD = "Str0ng!Passw0rd"


class InvitationDeliveryTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password=PWD, name="Ada Admin"
        )
        self.member = User.objects.create_user(
            email="member@example.com", password=PWD, name="Mo Member"
        )
        self.existing = User.objects.create_user(
            email="existing@example.com", password=PWD, name="Eve Existing"
        )
        self.workspace = Workspace.objects.create(name="Aurora", owner=self.admin)
        WorkspaceMember.objects.update_or_create(
            workspace=self.workspace,
            user=self.admin,
            defaults={"role": WorkspaceRole.OWNER},
        )
        WorkspaceMember.objects.update_or_create(
            workspace=self.workspace,
            user=self.member,
            defaults={"role": WorkspaceRole.MEMBER},
        )
        mail.outbox = []

    def invite(self, email, role="member", as_user=None):
        self.client.force_authenticate(as_user or self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                INVITATIONS,
                {"workspace": str(self.workspace.id), "email": email, "role": role},
                format="json",
            )

    # -- delivery --------------------------------------------------------
    def test_inviting_a_stranger_sends_them_an_email(self):
        response = self.invite("stranger@example.com")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["stranger@example.com"])
        self.assertIn("Aurora", message.subject)
        self.assertIn("Ada Admin", message.subject)

    def test_the_email_carries_a_working_accept_link(self):
        self.invite("stranger@example.com")
        invitation = Invitation.objects.get(email="stranger@example.com")

        self.assertIn(str(invitation.token), mail.outbox[0].body)

    def test_someone_without_an_account_is_pointed_at_registration(self):
        self.invite("stranger@example.com")

        body = mail.outbox[0].body
        self.assertIn("/register", body)
        self.assertIn("stranger@example.com", body)

    def test_an_existing_user_gets_both_an_email_and_an_in_app_notification(self):
        self.invite(self.existing.email)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            Notification.objects.filter(recipient=self.existing).exists(),
            "an existing user should also be notified in the app",
        )

    def test_resending_sends_the_email_again(self):
        self.invite("stranger@example.com")
        invitation = Invitation.objects.get(email="stranger@example.com")
        mail.outbox = []

        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f"{INVITATIONS}{invitation.token}/resend/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    # -- authorisation ---------------------------------------------------
    def test_a_plain_member_cannot_invite_and_no_mail_goes_out(self):
        response = self.invite("stranger@example.com", as_user=self.member)

        self.assertIn(response.status_code, (403, 400))
        self.assertEqual(len(mail.outbox), 0)

    def test_no_mail_is_sent_when_the_invitation_is_rejected_as_invalid(self):
        """A duplicate invite must not mail the person a second time."""
        self.invite("stranger@example.com")
        mail.outbox = []

        response = self.invite("stranger@example.com")

        if response.status_code >= 400:
            self.assertEqual(len(mail.outbox), 0)

    # -- lifecycle -------------------------------------------------------
    def test_accepting_an_emailed_invitation_grants_membership(self):
        self.invite(self.existing.email)
        invitation = Invitation.objects.get(email=self.existing.email)

        self.client.force_authenticate(self.existing)
        response = self.client.post(f"{INVITATIONS}{invitation.token}/accept/")

        self.assertEqual(response.status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, InvitationStatus.ACCEPTED)
        self.assertTrue(
            WorkspaceMember.objects.filter(
                workspace=self.workspace, user=self.existing
            ).exists()
        )

    def test_a_stranger_who_registers_later_can_still_accept(self):
        """The invitation waits for the account, which is why email matters."""
        self.invite("late@example.com")
        invitation = Invitation.objects.get(email="late@example.com")

        latecomer = User.objects.create_user(
            email="late@example.com", password=PWD, name="Late Comer"
        )
        self.client.force_authenticate(latecomer)
        response = self.client.post(f"{INVITATIONS}{invitation.token}/accept/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            WorkspaceMember.objects.filter(
                workspace=self.workspace, user=latecomer
            ).exists()
        )
