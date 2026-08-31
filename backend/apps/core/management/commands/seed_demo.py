"""
Seed a realistic demo dataset covering every surface in the app.

Creates three workspaces (so the workspace switcher and the role-gated
navigation are both exercised) and fills each one with projects, tasks,
documents, handovers, comments, mentions, notifications, invitations, activity
and AI content. Enum-backed fields are seeded across *all* of their values —
every task status/priority combination, every project status, every handover
and invitation state — so filters, charts and empty states all have something
to show.

    python manage.py seed_demo
    python manage.py seed_demo --owner-email you@example.com
    python manage.py seed_demo --reset                 # wipe previous demo data first
    python manage.py seed_demo --reset --skip-embedding # ...without the RAG pipeline

``--reset`` only removes the demo workspaces (matched by name) and accounts on
the ``@nexora.demo`` domain. Real accounts and their data are never touched.

Timestamps are backdated across the last eight weeks so the analytics charts,
the "overdue" counters and the audit-log date filters all have a real spread.
Everything is driven by a seeded RNG, so repeated runs produce the same shape.
"""

from __future__ import annotations

import datetime
import mimetypes
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.activities.models import Activity
from apps.activities.services import log_activity
from apps.ai.models import (
    AIConversation,
    AIMessage,
    AISettings,
    PromptTemplate,
    SearchHistory,
)
from apps.comments.models import Comment
from apps.core import demo_data as D
from apps.documents.models import Document
from apps.handovers.models import Handover, HandoverStatus
from apps.invitations.models import Invitation, InvitationStatus
from apps.knowledge.models import DocumentChunk, EmbeddingJob, EmbeddingStatus
from apps.knowledge.services.chunker import chunk_text
from apps.mentions.services import sync_comment_mentions
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import create_notification
from apps.projects.models import Project, ProjectStatus
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole

User = get_user_model()

# Statuses that count as "open" work (mirrors apps.core.views).
OPEN_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW)

# How far back the seeded history stretches. Eight weeks matches the window the
# analytics endpoint charts.
HISTORY_DAYS = 56


class Command(BaseCommand):
    help = "Seed demo workspaces with realistic data across every feature."

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------
    def add_arguments(self, parser):
        parser.add_argument(
            "--owner-email",
            default=f"demo.owner@{D.DEMO_DOMAIN}",
            help=(
                "Account that owns the main demo workspace. Pass your own login "
                "so the data shows up when you sign in. Created with the demo "
                "password if it doesn't exist; existing accounts are left alone."
            ),
        )
        parser.add_argument(
            "--password",
            default=D.DEMO_PASSWORD,
            help="Password for newly created demo accounts.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded demo workspaces and accounts first.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=20260731,
            help="RNG seed — same value produces the same dataset.",
        )
        parser.add_argument(
            "--skip-embedding",
            action="store_true",
            help=(
                "Don't run the real embedding pipeline on seeded documents "
                "(much faster; chunks are stored without vectors, so AI "
                "semantic search will return nothing)."
            ),
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.rng = random.Random(options["seed"])
        self.now = timezone.now()
        self.password = options["password"]
        if options["skip_embedding"]:
            # Detach the ingestion signal (apps.knowledge.handlers) for the run.
            from django.db.models.signals import post_save

            post_save.disconnect(
                sender=Document, dispatch_uid="knowledge_document_created"
            )
        # object pk (str) -> creation time, used to backdate the activity log.
        self.times: dict[str, datetime.datetime] = {}
        self.workspaces: list[Workspace] = []

        with transaction.atomic():
            if options["reset"]:
                self._reset()

            owner = self._get_or_create_owner(options["owner_email"])
            # The account the demo is viewed from — gets a deliberate share of
            # the work so "my tasks", overdue counters and received handovers
            # aren't empty on the dashboard.
            self.primary_user = owner
            people = self._create_people()

            self._seed_aurora(owner, people)
            self._seed_northwind(owner, people)
            self._seed_portal(owner, people)
            self._backdate_activities()

        self._report(owner)

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------
    def _ago(self, days: float, hours: int = 0) -> datetime.datetime:
        return self.now - datetime.timedelta(days=days, hours=hours)

    def _random_past(self, max_days: int = HISTORY_DAYS, min_days: int = 0):
        """A random past instant, weighted towards the recent end."""
        span = max_days - min_days
        # Squaring a uniform draw biases towards 0 -> towards "recent".
        offset = min_days + span * (self.rng.random() ** 2)
        return self.now - datetime.timedelta(
            days=offset,
            hours=self.rng.randint(0, 23),
            minutes=self.rng.randint(0, 59),
        )

    def _stamp(self, obj, created, updated=None):
        """Force ``created_at``/``updated_at`` (both are auto-managed fields)."""
        updated = updated or created
        type(obj).objects.filter(pk=obj.pk).update(
            created_at=created, updated_at=updated
        )
        obj.created_at, obj.updated_at = created, updated
        self.times[str(obj.pk)] = created
        return obj

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def _reset(self):
        workspaces = Workspace.objects.filter(name__in=D.WORKSPACE_NAMES)
        # Remove the stored files too — deleting the row doesn't touch storage.
        for document in Document.objects.filter(workspace__in=workspaces):
            if document.file:
                document.file.delete(save=False)
        workspace_ids = list(workspaces.values_list("id", flat=True))
        deleted_ws = len(workspace_ids)
        workspaces.delete()
        # The cascade fires post_delete handlers, which log fresh activity rows
        # pointing at workspaces that no longer exist. Clear them before the
        # deferred foreign key is checked at COMMIT.
        Activity.objects.filter(workspace_id__in=workspace_ids).delete()

        demo_users = User.objects.filter(email__endswith=f"@{D.DEMO_DOMAIN}")
        deleted_users = demo_users.count()
        demo_users.delete()

        self.stdout.write(
            self.style.WARNING(
                f"Reset: removed {deleted_ws} demo workspace(s) and "
                f"{deleted_users} demo account(s)."
            )
        )

    # ------------------------------------------------------------------
    # People
    # ------------------------------------------------------------------
    def _get_or_create_owner(self, email: str):
        owner = User.objects.filter(email__iexact=email).first()
        if owner:
            self.owner_is_new = False
            return owner
        owner = User.objects.create_user(
            email=email,
            password=self.password,
            name="Demo Owner",
            avatar=self._avatar("Demo Owner"),
        )
        self.owner_is_new = True
        return owner

    def _avatar(self, name: str) -> str:
        slug = name.replace(" ", "+")
        return f"https://api.dicebear.com/9.x/initials/svg?seed={slug}"

    def _create_people(self) -> dict:
        people = {}
        for index, (key, name) in enumerate(D.PEOPLE.items()):
            email = f"{key}@{D.DEMO_DOMAIN}"
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=self.password,
                    name=name,
                    avatar=self._avatar(name),
                )
            joined = self._ago(HISTORY_DAYS + 30 - index * 2)
            User.objects.filter(pk=user.pk).update(
                date_joined=joined, created_at=joined, updated_at=joined
            )
            people[key] = user
        return people

    def _workspace(self, *, name, description, owner, roster, created_days_ago):
        """Create a workspace plus its membership rows."""
        workspace = Workspace.objects.create(
            name=name, description=description, owner=owner
        )
        created = self._ago(created_days_ago)
        self._stamp(workspace, created)
        self.workspaces.append(workspace)

        members = []
        for index, (user, role) in enumerate(roster):
            member = WorkspaceMember.objects.create(
                workspace=workspace, user=user, role=role
            )
            joined = created + datetime.timedelta(days=index * 0.7, hours=index)
            WorkspaceMember.objects.filter(pk=member.pk).update(
                created_at=joined, updated_at=joined, joined_at=joined
            )
            self.times[str(member.pk)] = joined
            members.append(user)
        return workspace, members

    # ------------------------------------------------------------------
    # Projects & tasks
    # ------------------------------------------------------------------
    def _create_projects(self, workspace, specs, members):
        projects = []
        for index, (name, status, color, archived, description) in enumerate(specs):
            author = members[index % len(members)]
            project = Project.objects.create(
                workspace=workspace,
                name=name,
                description=description,
                color=color,
                status=status,
                archived=archived,
                owner=members[(index + 1) % len(members)],
                created_by=author,
                updated_by=author,
            )
            created = self._ago(HISTORY_DAYS - index * 2, hours=index)
            self._stamp(project, created)
            projects.append(project)
        return projects

    def _task_combos(self):
        """Every (status, priority) pair, shuffled but exhaustive."""
        combos = [
            (status, priority)
            for status in TaskStatus.values
            for priority in TaskPriority.values
        ]
        self.rng.shuffle(combos)
        return combos

    def _create_tasks(self, workspace, projects, members, *, exhaustive=True):
        combos = self._task_combos()
        combo_index = 0
        seen_combos = set()
        tasks = []

        for project in projects:
            titles = D.TASK_TITLES.get(project.name, [])
            for title in titles:
                if project.status == ProjectStatus.COMPLETED or project.archived:
                    # Finished projects hold finished work.
                    status = self.rng.choice(
                        [TaskStatus.COMPLETED] * 4 + [TaskStatus.CANCELLED]
                    )
                    priority = self.rng.choice(TaskPriority.values)
                else:
                    status, priority = combos[combo_index % len(combos)]
                    combo_index += 1
                seen_combos.add((status, priority))
                tasks.append(
                    self._create_task(workspace, project, members, title, status, priority)
                )

        if exhaustive:
            # Backfill any combination the title pool didn't reach, so every
            # status/priority filter returns rows.
            filler_project = projects[0]
            for status, priority in combos:
                if (status, priority) in seen_combos:
                    continue
                title = f"Review {status.replace('_', ' ')} / {priority} backlog item"
                tasks.append(
                    self._create_task(
                        workspace, filler_project, members, title, status, priority
                    )
                )
        return tasks

    def _create_task(self, workspace, project, members, title, status, priority):
        rng = self.rng
        reporter = rng.choice(members)
        roll = rng.random()
        if roll < 0.1:
            assignee = None  # ~1 in 10 tasks is deliberately unassigned
        elif roll < 0.32 and self.primary_user in members:
            assignee = self.primary_user
        else:
            assignee = rng.choice(members)

        created = self._random_past(HISTORY_DAYS)
        if status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            # Closed some time after creation, but never in the future.
            updated = min(
                created + datetime.timedelta(days=rng.uniform(0.5, 18)), self.now
            )
        else:
            updated = min(
                created + datetime.timedelta(days=rng.uniform(0, 6)), self.now
            )

        due_date = self._due_date_for(status, created)
        start_date = (
            created.date() + datetime.timedelta(days=rng.randint(0, 3))
            if rng.random() < 0.6
            else None
        )
        labels = rng.sample(D.TASK_LABELS, rng.choice([0, 1, 2, 2, 3]))
        estimate = rng.choice([None, 1, 2, 3, 5, 8, 13, 21, 40])

        task = Task.objects.create(
            workspace=workspace,
            project=project,
            title=title,
            description=rng.choice(D.TASK_DESCRIPTIONS).format(title=title),
            status=status,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            due_date=due_date,
            start_date=start_date,
            estimated_hours=Decimal(str(estimate)) if estimate else None,
            labels=labels,
            created_by=reporter,
            updated_by=assignee or reporter,
        )
        return self._stamp(task, created, updated)

    def _due_date_for(self, status, created):
        rng = self.rng
        today = self.now.date()
        if status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            if rng.random() < 0.2:
                return None
            return created.date() + datetime.timedelta(days=rng.randint(3, 20))

        bucket = rng.random()
        if bucket < 0.3:  # overdue — drives the dashboard's "overdue" tile
            return today - datetime.timedelta(days=rng.randint(1, 14))
        if bucket < 0.38:  # due today
            return today
        if bucket < 0.62:  # this week
            return today + datetime.timedelta(days=rng.randint(1, 7))
        if bucket < 0.85:  # this month
            return today + datetime.timedelta(days=rng.randint(8, 30))
        return None  # no due date at all

    # ------------------------------------------------------------------
    # Documents & knowledge
    # ------------------------------------------------------------------
    def _create_documents(self, workspace, specs, projects, members):
        documents = []
        for index, (filename, title, description, body) in enumerate(specs):
            uploader = members[index % len(members)]
            # Every other document is filed under a project; the rest sit at
            # workspace level (both are valid and both render differently).
            project = projects[index % len(projects)] if index % 2 == 0 else None
            payload = body.encode("utf-8")

            document = Document(
                workspace=workspace,
                project=project,
                title=title,
                description=description,
                file_type=mimetypes.guess_type(filename)[0] or "text/plain",
                file_size=len(payload),
                uploaded_by=uploader,
                created_by=uploader,
                updated_by=uploader,
            )
            document.file.save(filename, ContentFile(payload), save=False)
            document.save()
            created = self._random_past(HISTORY_DAYS - 4, min_days=1)
            self._stamp(document, created)
            documents.append(document)
            self._index_document(document, body, index, created)
        return documents

    def _index_document(self, document, body, index, created):
        """Normalise the knowledge-layer rows for a freshly created document.

        Saving a Document already fires ``knowledge.handlers`` which runs the
        real extract → chunk → embed pipeline inline. This method fills the gaps
        that leaves for a demo dataset: chunk rows without vectors when no local
        embedding model is available, a failure row for the unsupported file
        type, and backdated job timestamps.
        """
        supported = document.file.name.lower().endswith((".md", ".txt", ".markdown"))
        job = document.embedding_jobs.order_by("-created_at").first()

        if not supported:
            # The signal skips unsupported files silently — record the skip so
            # the document's indexing state is visible in the UI.
            if job is None:
                job = EmbeddingJob.objects.create(
                    workspace=document.workspace,
                    document=document,
                    status=EmbeddingStatus.FAILED,
                    error="Unsupported document type: cannot extract text.",
                    provider="sentence_transformer",
                    model="all-MiniLM-L6-v2",
                )
        elif not document.chunks.exists():
            # No local embedding model: keep the demo useful by storing the
            # chunks anyway, with null vectors (semantic search will skip them).
            chunks = chunk_text(body)
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        workspace=document.workspace,
                        document=document,
                        content=chunk["content"],
                        chunk_index=chunk["chunk_index"],
                        token_count=chunk["token_count"],
                        embedding=None,
                        metadata={"title": document.title},
                    )
                    for chunk in chunks
                ]
            )
            if job is None:
                job = EmbeddingJob.objects.create(
                    workspace=document.workspace, document=document
                )
            EmbeddingJob.objects.filter(pk=job.pk).update(
                status=EmbeddingStatus.COMPLETED,
                chunk_count=len(chunks),
                error="",
                provider="sentence_transformer",
                model="all-MiniLM-L6-v2",
            )

        if job is not None:
            EmbeddingJob.objects.filter(pk=job.pk).update(
                created_at=created,
                updated_at=created,
                started_at=created,
                finished_at=created + datetime.timedelta(seconds=9),
            )
            self.times[str(job.pk)] = created

        # Two documents also carry a *re-index* job that never finished, so the
        # pending and processing states are represented somewhere.
        if supported and index == 3:
            EmbeddingJob.objects.create(
                workspace=document.workspace,
                document=document,
                status=EmbeddingStatus.PROCESSING,
                provider="sentence_transformer",
                model="all-MiniLM-L6-v2",
                started_at=self._ago(0, hours=1),
            )
        elif supported and index == 5:
            EmbeddingJob.objects.create(
                workspace=document.workspace,
                document=document,
                status=EmbeddingStatus.PENDING,
                provider="sentence_transformer",
                model="all-MiniLM-L6-v2",
            )

    # ------------------------------------------------------------------
    # Handovers
    # ------------------------------------------------------------------
    def _create_handovers(self, workspace, tasks, members, reviewers, specs, plan):
        """``plan`` is a list of (status, content_index) tuples."""
        handovers = []
        # Prefer in-flight tasks — handing over finished work is unusual.
        candidates = [t for t in tasks if t.status in OPEN_STATUSES and t.assignee]
        self.rng.shuffle(candidates)

        for slot, (status, content_index) in enumerate(plan):
            if slot >= len(candidates):
                break
            task = candidates[slot]
            summary, pending, resources = specs[content_index % len(specs)]
            from_user = task.assignee
            others = [m for m in members if m != from_user]
            # Send a third of handovers *to* the viewing account so the
            # "received" tab and its notifications aren't empty.
            if self.rng.random() < 0.35 and self.primary_user in others:
                to_user = self.primary_user
            else:
                to_user = self.rng.choice(others)

            handover = Handover.objects.create(
                workspace=workspace,
                task=task,
                from_user=from_user,
                to_user=to_user,
                summary=summary,
                pending_items=pending,
                resources=resources,
                status=HandoverStatus.PENDING,
                created_by=from_user,
                updated_by=from_user,
            )
            created = self._random_past(30, min_days=1)
            self._stamp(handover, created)

            create_notification(
                recipient=to_user,
                actor=from_user,
                workspace=workspace,
                type=NotificationType.HANDOVER_SUBMITTED,
                title=f"{from_user.name} handed over “{task.title}”",
                message="Pending manager review.",
                link=f"/handovers/{handover.id}",
            )

            if status != HandoverStatus.PENDING:
                self._review_handover(handover, task, reviewers, status, created)

            handovers.append(handover)
        return handovers

    def _review_handover(self, handover, task, reviewers, decision, created):
        reviewer = self.rng.choice(
            [r for r in reviewers if r not in (handover.from_user, handover.to_user)]
            or reviewers
        )
        wait_hours = self.rng.uniform(2, 72)
        reviewed_at = min(created + datetime.timedelta(hours=wait_hours), self.now)

        handover.status = decision
        handover.reviewer = reviewer
        handover.reviewed_at = reviewed_at
        handover.updated_by = reviewer
        handover.review_comment = self.rng.choice(
            D.REVIEW_COMMENTS_APPROVED
            if decision == HandoverStatus.APPROVED
            else D.REVIEW_COMMENTS_REJECTED
        )
        handover.save()
        self._stamp(handover, created, reviewed_at)

        if decision == HandoverStatus.APPROVED:
            # Mirrors the review endpoint: approval reassigns the task.
            task.assignee = handover.to_user
            task.updated_by = reviewer
            task.save(update_fields=["assignee", "updated_by", "updated_at"])
            Task.objects.filter(pk=task.pk).update(updated_at=reviewed_at)

        for recipient in (handover.from_user, handover.to_user):
            create_notification(
                recipient=recipient,
                actor=reviewer,
                workspace=handover.workspace,
                type=NotificationType.HANDOVER_REVIEWED,
                title=f"Handover {decision}: “{task.title}”",
                message=handover.review_comment,
                link=f"/handovers/{handover.id}",
            )

    # ------------------------------------------------------------------
    # Comments, mentions
    # ------------------------------------------------------------------
    def _mention_token(self, user) -> str:
        return f"@[{user.name or user.email}]({user.id})"

    def _create_comments(self, workspace, targets, members):
        comments = []
        for target in targets:
            for _ in range(self.rng.randint(1, 3)):
                author = self.rng.choice(members)
                others = [m for m in members if m != author]
                body = self.rng.choice(D.COMMENT_SEEDS)
                body = body.replace("{m}", self._mention_token(self.rng.choice(others)))

                comment = self._comment(workspace, target, author, body)
                comments.append(comment)

                if self.rng.random() < 0.45:
                    replier = self.rng.choice(others)
                    reply = self._comment(
                        workspace,
                        target,
                        replier,
                        self.rng.choice(D.COMMENT_REPLIES),
                        parent=comment,
                    )
                    comments.append(reply)
                    create_notification(
                        recipient=author,
                        actor=replier,
                        workspace=workspace,
                        type=NotificationType.COMMENT_REPLY,
                        title=f"{replier.name} replied to your comment",
                        message=reply.content[:120],
                        link=self._link_for(target),
                    )
        return comments

    def _comment(self, workspace, target, author, content, parent=None):
        from django.contrib.contenttypes.models import ContentType

        comment = Comment.objects.create(
            workspace=workspace,
            author=author,
            content=content,
            parent=parent,
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.pk,
        )
        base = self.times.get(str(target.pk), self._ago(HISTORY_DAYS))
        created = min(
            base + datetime.timedelta(days=self.rng.uniform(0.2, 12)), self.now
        )
        self._stamp(comment, created)
        # Generates Mention rows + mention notifications via the mentions signal.
        sync_comment_mentions(comment)
        return comment

    def _link_for(self, target) -> str:
        prefix = {
            "Project": "/projects/",
            "Task": "/tasks/",
            "Document": "/documents/",
        }[target.__class__.__name__]
        return f"{prefix}{target.pk}"

    # ------------------------------------------------------------------
    # Notifications & invitations
    # ------------------------------------------------------------------
    def _create_notifications(self, workspace, owner, members, tasks, projects):
        """Explicitly cover the notification types signals don't produce."""
        actors = [m for m in members if m != owner] or members
        open_tasks = [t for t in tasks if t.status in OPEN_STATUSES][:6]

        for index, task in enumerate(open_tasks):
            actor = actors[index % len(actors)]
            create_notification(
                recipient=owner,
                actor=actor,
                workspace=workspace,
                type=(
                    NotificationType.TASK_ASSIGNED
                    if index % 2 == 0
                    else NotificationType.TASK_UPDATED
                ),
                title=(
                    f"{actor.name} assigned you “{task.title}”"
                    if index % 2 == 0
                    else f"{actor.name} updated “{task.title}”"
                ),
                message=f"In {task.project.name} · priority {task.priority}.",
                link=f"/tasks/{task.id}",
            )

        for type_, title, message in D.SYSTEM_NOTIFICATIONS:
            create_notification(
                recipient=owner,
                actor=None,
                workspace=workspace,
                type=type_,
                title=title,
                message=message,
                link=f"/projects/{projects[0].id}",
            )

        # Spread notifications over time and mark a realistic share as read.
        for notification in Notification.objects.filter(workspace=workspace):
            created = self._random_past(21)
            Notification.objects.filter(pk=notification.pk).update(
                created_at=created,
                updated_at=created,
                is_read=self.rng.random() < 0.45,
            )

    def _create_invitations(self, workspace, inviter, plan):
        """``plan``: list of (email_local, role, status)."""
        for local, role, status in plan:
            email = f"{local}@{D.DEMO_DOMAIN}"
            expires = self.now + datetime.timedelta(days=7)
            if status == InvitationStatus.EXPIRED:
                expires = self._ago(2)

            invitation = Invitation.objects.create(
                workspace=workspace,
                email=email,
                invited_by=inviter,
                role=role,
                status=status,
                expires_at=expires,
            )
            created = self._random_past(20, min_days=1)
            self._stamp(invitation, created)
            # The invite endpoint logs this; seeding bypasses the endpoint.
            log_activity(
                actor=inviter,
                workspace=workspace,
                action="member.invited",
                metadata={"email": email, "role": role},
            )

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------
    def _seed_ai(self, workspace, owner, members, documents, *, provider, model):
        AISettings.objects.update_or_create(
            workspace=workspace,
            defaults={
                "is_enabled": True,
                "provider": provider,
                "chat_model": model,
                "embedding_provider": "sentence_transformer",
                "embedding_model": "all-MiniLM-L6-v2",
                "temperature": 0.2,
                "max_tokens": 1024,
            },
        )

        for index, (title, turns) in enumerate(D.AI_CONVERSATIONS):
            conversation = AIConversation.objects.create(
                workspace=workspace,
                user=owner,
                title=title,
                created_by=owner,
                updated_by=owner,
            )
            started = self._random_past(24, min_days=1)
            last = started
            for turn_index, (role, content) in enumerate(turns):
                message = AIMessage.objects.create(
                    conversation=conversation,
                    role=role,
                    content=content,
                    sources=(
                        self._sources_for(documents)
                        if role == "assistant" and documents
                        else []
                    ),
                    token_count=max(12, len(content.split())),
                    metadata=(
                        {"provider": provider, "model": model, "confidence": "high"}
                        if role == "assistant"
                        else {}
                    ),
                )
                last = started + datetime.timedelta(minutes=turn_index * 2)
                self._stamp(message, last)
            self._stamp(conversation, started, last)

        for query in D.AI_SEARCH_QUERIES:
            history = SearchHistory.objects.create(
                workspace=workspace,
                user=owner,
                query=query,
                results_count=self.rng.randint(0, 6),
                top_score=round(self.rng.uniform(0.31, 0.88), 4),
            )
            self._stamp(history, self._random_past(18))

        for name, category, description, template, shared in D.PROMPT_TEMPLATES:
            author = self.rng.choice(members)
            prompt = PromptTemplate.objects.create(
                workspace=workspace,
                name=name,
                description=description,
                category=category,
                template=template,
                is_shared=shared,
                created_by=author,
                updated_by=author,
            )
            self._stamp(prompt, self._random_past(40, min_days=2))

    def _sources_for(self, documents):
        picks = self.rng.sample(documents, min(2, len(documents)))
        sources = []
        for document in picks:
            chunk = document.chunks.first()
            if chunk is None:
                continue
            sources.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "title": document.title,
                    "content": chunk.content[:400],
                    "chunk_index": chunk.chunk_index,
                    "score": round(self.rng.uniform(0.55, 0.86), 4),
                }
            )
        return sources

    # ------------------------------------------------------------------
    # Edits & deletions — so the audit log carries every action verb
    # ------------------------------------------------------------------
    def _make_edit_history(self, workspace, projects, tasks, documents, members):
        editor = members[0]

        workspace.description = f"{workspace.description} Updated after the quarterly planning review."
        workspace.save()

        for project in projects[:2]:
            project.description = f"{project.description} Scope refreshed this sprint."
            project.updated_by = editor
            project.save()
            self._stamp(project, project.created_at, self._random_past(10))

        for task in tasks[:6]:
            task.updated_by = editor
            task.save()
            Task.objects.filter(pk=task.pk).update(updated_at=self._random_past(9))

        for document in documents[:2]:
            document.description = f"{document.description} Reviewed and re-published."
            document.updated_by = editor
            document.save()
            self._stamp(document, document.created_at, self._random_past(8))

    def _make_deletion_history(self, workspace, members):
        """Create-then-delete a few objects so ``*.deleted`` actions exist."""
        actor = members[0]

        project = Project.objects.create(
            workspace=workspace,
            name="Spike: real-time collaboration",
            description="Timeboxed spike. Closed out and removed after the readout.",
            status=ProjectStatus.PLANNING,
            owner=actor,
            created_by=actor,
            updated_by=actor,
        )
        task = Task.objects.create(
            workspace=workspace,
            project=project,
            title="Prototype CRDT merge for documents",
            status=TaskStatus.CANCELLED,
            priority=TaskPriority.LOW,
            assignee=actor,
            reporter=actor,
            created_by=actor,
            updated_by=actor,
        )
        payload = b"Spike readout: CRDT merge is viable but not this quarter.\n"
        document = Document(
            workspace=workspace,
            title="Spike readout (superseded)",
            description="Replaced by ADR-014.",
            file_type="text/plain",
            file_size=len(payload),
            uploaded_by=actor,
            created_by=actor,
            updated_by=actor,
        )
        document.file.save("spike-readout.txt", ContentFile(payload), save=False)
        document.save()
        handover = Handover.objects.create(
            workspace=workspace,
            task=task,
            from_user=actor,
            to_user=members[1],
            summary="Spike handover, withdrawn before review.",
            status=HandoverStatus.PENDING,
            created_by=actor,
            updated_by=actor,
        )

        handover.delete()
        document.file.delete(save=False)
        document.delete()
        task.delete()
        project.delete()

        # A member who joined and then left.
        leaver = User.objects.filter(email=f"noah@{D.DEMO_DOMAIN}").first()
        if leaver and not WorkspaceMember.objects.filter(
            workspace=workspace, user=leaver
        ).exists():
            membership = WorkspaceMember.objects.create(
                workspace=workspace, user=leaver, role=WorkspaceRole.MEMBER
            )
            membership.delete()

    # ------------------------------------------------------------------
    # Activity backdating
    # ------------------------------------------------------------------
    def _backdate_activities(self):
        """Activity rows are written by signals *now* — spread them out."""
        for activity in Activity.objects.filter(workspace__in=self.workspaces):
            when = self.times.get(str(activity.object_id)) if activity.object_id else None
            if when is None:
                when = self._random_past(HISTORY_DAYS)
            if activity.action.endswith(".updated"):
                when = min(when + datetime.timedelta(days=self.rng.uniform(1, 12)), self.now)
            elif activity.action.endswith(".deleted"):
                when = self._random_past(14)
            Activity.objects.filter(pk=activity.pk).update(
                created_at=when, updated_at=when
            )

    # ------------------------------------------------------------------
    # Workspace builders
    # ------------------------------------------------------------------
    def _seed_aurora(self, owner, people):
        roster = [
            (owner, WorkspaceRole.OWNER),
            (people["maya"], WorkspaceRole.ADMIN),
            (people["omar"], WorkspaceRole.MANAGER),
            (people["priya"], WorkspaceRole.MANAGER),
            (people["liam"], WorkspaceRole.MEMBER),
            (people["sofia"], WorkspaceRole.MEMBER),
            (people["tom"], WorkspaceRole.MEMBER),
            (people["ines"], WorkspaceRole.MEMBER),
            (people["rahul"], WorkspaceRole.MEMBER),
            (people["yuki"], WorkspaceRole.MEMBER),
        ]
        workspace, members = self._workspace(
            name="Aurora Labs",
            description=(
                "Product engineering org: platform rewrite, mobile app, design "
                "system, billing and compliance."
            ),
            owner=owner,
            roster=roster,
            created_days_ago=HISTORY_DAYS + 14,
        )
        reviewers = [owner, people["maya"], people["omar"], people["priya"]]

        projects = self._create_projects(workspace, D.AURORA_PROJECTS, members)
        tasks = self._create_tasks(workspace, projects, members)
        documents = self._create_documents(workspace, D.DOCUMENTS, projects, members)

        plan = [
            (HandoverStatus.PENDING, 0),
            (HandoverStatus.PENDING, 1),
            (HandoverStatus.PENDING, 2),
            (HandoverStatus.APPROVED, 3),
            (HandoverStatus.APPROVED, 4),
            (HandoverStatus.APPROVED, 0),
            (HandoverStatus.REJECTED, 1),
            (HandoverStatus.REJECTED, 5),
            (HandoverStatus.APPROVED, 2),
            (HandoverStatus.PENDING, 3),
        ]
        self._create_handovers(
            workspace, tasks, members, reviewers, D.HANDOVER_CONTENT, plan
        )

        commentable = (
            projects[:3]
            + [t for t in tasks if t.status in OPEN_STATUSES][:10]
            + documents[:3]
        )
        self._create_comments(workspace, commentable, members)
        self._create_notifications(workspace, owner, members, tasks, projects)
        self._create_invitations(
            workspace,
            owner,
            [
                ("new.designer", WorkspaceRole.MEMBER, InvitationStatus.PENDING),
                ("new.analyst", WorkspaceRole.MEMBER, InvitationStatus.PENDING),
                ("elena", WorkspaceRole.MANAGER, InvitationStatus.ACCEPTED),
                ("contractor", WorkspaceRole.MEMBER, InvitationStatus.REJECTED),
                ("old.invite", WorkspaceRole.MEMBER, InvitationStatus.EXPIRED),
                ("wrong.address", WorkspaceRole.ADMIN, InvitationStatus.CANCELLED),
            ],
        )
        self._seed_ai(
            workspace,
            owner,
            members,
            documents,
            provider="gemini",
            model="gemini-2.0-flash",
        )
        self._make_edit_history(workspace, projects, tasks, documents, members)
        self._make_deletion_history(workspace, members)

    def _seed_northwind(self, owner, people):
        roster = [
            (people["maya"], WorkspaceRole.OWNER),
            (owner, WorkspaceRole.MANAGER),
            (people["omar"], WorkspaceRole.ADMIN),
            (people["liam"], WorkspaceRole.MEMBER),
            (people["sofia"], WorkspaceRole.MEMBER),
            (people["elena"], WorkspaceRole.MEMBER),
        ]
        workspace, members = self._workspace(
            name="Northwind Ops",
            description="Operations, on-call and vendor management.",
            owner=people["maya"],
            roster=roster,
            created_days_ago=HISTORY_DAYS + 4,
        )
        reviewers = [people["maya"], owner, people["omar"]]

        projects = self._create_projects(workspace, D.NORTHWIND_PROJECTS, members)
        tasks = self._create_tasks(workspace, projects, members, exhaustive=False)
        documents = self._create_documents(
            workspace, D.NORTHWIND_DOCUMENTS, projects, members
        )
        self._create_handovers(
            workspace,
            tasks,
            members,
            reviewers,
            D.HANDOVER_CONTENT[5:],
            [
                (HandoverStatus.PENDING, 0),
                (HandoverStatus.PENDING, 1),
                (HandoverStatus.APPROVED, 2),
            ],
        )
        self._create_comments(
            workspace,
            projects[:2] + [t for t in tasks if t.status in OPEN_STATUSES][:4],
            members,
        )
        self._create_notifications(workspace, owner, members, tasks, projects)
        self._create_invitations(
            workspace,
            people["maya"],
            [
                ("ops.hire", WorkspaceRole.MEMBER, InvitationStatus.PENDING),
                ("noah", WorkspaceRole.MEMBER, InvitationStatus.ACCEPTED),
            ],
        )
        self._seed_ai(
            workspace,
            owner,
            members,
            documents,
            provider="openai",
            model="gpt-4o-mini",
        )

    def _seed_portal(self, owner, people):
        roster = [
            (people["omar"], WorkspaceRole.OWNER),
            (people["priya"], WorkspaceRole.ADMIN),
            (owner, WorkspaceRole.MEMBER),
            (people["tom"], WorkspaceRole.MEMBER),
        ]
        workspace, members = self._workspace(
            name="Client Portal",
            description=(
                "External-facing portal work. Seeded with the demo owner as a "
                "plain member so role-gated navigation can be compared."
            ),
            owner=people["omar"],
            roster=roster,
            created_days_ago=30,
        )
        projects = self._create_projects(workspace, D.PORTAL_PROJECTS, members)
        tasks = self._create_tasks(workspace, projects, members, exhaustive=False)
        documents = self._create_documents(
            workspace, D.PORTAL_DOCUMENTS, projects, members
        )
        self._create_handovers(
            workspace,
            tasks,
            members,
            [people["omar"], people["priya"]],
            D.HANDOVER_CONTENT[7:],
            [(HandoverStatus.PENDING, 0)],
        )
        self._create_comments(workspace, projects + tasks[:3], members)
        self._create_notifications(workspace, owner, members, tasks, projects)
        self._seed_ai(
            workspace,
            owner,
            members,
            documents,
            provider="ollama",
            model="llama3.1",
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def _report(self, owner):
        workspaces = Workspace.objects.filter(name__in=D.WORKSPACE_NAMES)
        counts = [
            ("workspaces", workspaces.count()),
            ("members", WorkspaceMember.objects.filter(workspace__in=workspaces).count()),
            ("projects", Project.objects.filter(workspace__in=workspaces).count()),
            ("tasks", Task.objects.filter(workspace__in=workspaces).count()),
            ("documents", Document.objects.filter(workspace__in=workspaces).count()),
            ("doc chunks", DocumentChunk.objects.filter(workspace__in=workspaces).count()),
            ("embedding jobs", EmbeddingJob.objects.filter(workspace__in=workspaces).count()),
            ("handovers", Handover.objects.filter(workspace__in=workspaces).count()),
            ("comments", Comment.objects.filter(workspace__in=workspaces).count()),
            ("notifications", Notification.objects.filter(workspace__in=workspaces).count()),
            ("invitations", Invitation.objects.filter(workspace__in=workspaces).count()),
            ("activities", Activity.objects.filter(workspace__in=workspaces).count()),
            ("ai conversations", AIConversation.objects.filter(workspace__in=workspaces).count()),
            ("ai messages", AIMessage.objects.filter(conversation__workspace__in=workspaces).count()),
            ("prompt templates", PromptTemplate.objects.filter(workspace__in=workspaces).count()),
            ("search history", SearchHistory.objects.filter(workspace__in=workspaces).count()),
        ]
        self.stdout.write(self.style.SUCCESS("\nSeeded demo data:"))
        for label, value in counts:
            self.stdout.write(f"  {label:<18} {value}")

        self.stdout.write(self.style.SUCCESS("\nSign in as:"))
        if getattr(self, "owner_is_new", False):
            self.stdout.write(f"  {owner.email} / {self.password}   (owner of Aurora Labs)")
        else:
            self.stdout.write(
                f"  {owner.email} — existing account, password unchanged "
                "(owner of Aurora Labs)"
            )
        self.stdout.write(
            f"  any of {', '.join(k + '@' + D.DEMO_DOMAIN for k in list(D.PEOPLE)[:3])}"
            f", … / {self.password}"
        )
        embedded = DocumentChunk.objects.filter(
            workspace__in=workspaces, embedding__isnull=False
        ).count()
        total_chunks = DocumentChunk.objects.filter(workspace__in=workspaces).count()
        if embedded:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{embedded}/{total_chunks} chunks carry embeddings — AI "
                    "semantic search and chat retrieval are live."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nChunks were stored without vectors, so AI semantic search "
                    "returns nothing. Re-run without --skip-embedding (needs a "
                    "working sentence-transformers install)."
                )
            )
