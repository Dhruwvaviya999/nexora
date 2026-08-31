"""
Static content for the ``seed_demo`` management command.

Kept out of the command module so the seeding *logic* stays readable. Nothing
here touches the database — these are plain literals describing the fictional
"Aurora Labs" organisation used for demos and screenshots.
"""

from __future__ import annotations

# Every seeded user gets this email domain, which is also how ``--reset``
# recognises demo accounts. Real accounts are never touched.
DEMO_DOMAIN = "nexora.demo"
DEMO_PASSWORD = "Demo@12345"

# Workspaces are matched by name for ``--reset``.
WORKSPACE_NAMES = ("Aurora Labs", "Northwind Ops", "Client Portal")


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
# key -> display name. Emails are derived as "<key>@nexora.demo".
PEOPLE = {
    "maya": "Maya Chen",
    "omar": "Omar Haddad",
    "priya": "Priya Nair",
    "liam": "Liam Novak",
    "sofia": "Sofia Reyes",
    "tom": "Tom Okafor",
    "ines": "Ines Dubois",
    "rahul": "Rahul Mehta",
    "yuki": "Yuki Tanaka",
    "elena": "Elena Petrova",
    "noah": "Noah Bergstrom",
}


# ---------------------------------------------------------------------------
# Projects — (name, status, colour, archived, description)
# Statuses cover every ProjectStatus value, plus an archived project.
# ---------------------------------------------------------------------------
AURORA_PROJECTS = [
    (
        "Atlas Platform Rewrite",
        "active",
        "#6366f1",
        False,
        "Incremental rewrite of the monolith into service boundaries. Ships "
        "behind feature flags; no big-bang cutover.",
    ),
    (
        "Mobile App v3",
        "active",
        "#06b6d4",
        False,
        "Offline-first rebuild of the customer app with a shared design system "
        "and a new sync engine.",
    ),
    (
        "Design System 2.0",
        "active",
        "#ec4899",
        False,
        "Token-driven components, dark mode parity and accessibility audits "
        "for every primitive.",
    ),
    (
        "Billing & Invoicing",
        "planning",
        "#f59e0b",
        False,
        "Usage-based billing, dunning flows, tax handling and a self-serve "
        "invoice portal. Scoping in progress.",
    ),
    (
        "Data Warehouse Migration",
        "on_hold",
        "#a855f7",
        False,
        "Move reporting off the primary database. Paused until the Q3 "
        "infrastructure budget is approved.",
    ),
    (
        "Q2 Compliance Audit",
        "completed",
        "#10b981",
        False,
        "SOC 2 Type II evidence collection, access reviews and remediation. "
        "Closed with zero major findings.",
    ),
    (
        "Legacy CRM Sunset",
        "completed",
        "#64748b",
        True,
        "Decommissioned the 2018 CRM after migrating accounts and history. "
        "Archived for reference.",
    ),
]

NORTHWIND_PROJECTS = [
    (
        "Incident Response",
        "active",
        "#ef4444",
        False,
        "On-call rotation, runbooks and post-incident reviews for the "
        "production fleet.",
    ),
    (
        "Vendor Onboarding",
        "planning",
        "#0ea5e9",
        False,
        "Security review, contract templates and procurement checklist for new "
        "suppliers.",
    ),
    (
        "Warehouse Automation",
        "on_hold",
        "#f97316",
        False,
        "Barcode scanning and pick-path optimisation. Blocked on hardware "
        "procurement.",
    ),
]

PORTAL_PROJECTS = [
    (
        "Client Portal MVP",
        "active",
        "#8b5cf6",
        False,
        "Read-only status portal for external clients: milestones, documents "
        "and deliverable sign-off.",
    ),
    (
        "Brand Refresh",
        "planning",
        "#14b8a6",
        False,
        "New logotype, palette and marketing site templates.",
    ),
]


# ---------------------------------------------------------------------------
# Task titles per project. Statuses/priorities/dates are assigned by the
# seeder so that every enum combination appears somewhere.
# ---------------------------------------------------------------------------
TASK_TITLES = {
    "Atlas Platform Rewrite": [
        "Extract the billing service from the monolith",
        "Introduce a shared request-context middleware",
        "Add contract tests between gateway and identity",
        "Migrate session storage to Redis",
        "Backfill audit columns on legacy tables",
        "Cut over read traffic behind the atlas-read flag",
        "Instrument p95 latency dashboards per endpoint",
        "Retire the v0 internal RPC client",
        "Document the service boundary decision record",
        "Load-test the new gateway at 3x peak",
    ],
    "Mobile App v3": [
        "Design the offline sync conflict-resolution rules",
        "Implement incremental sync for the tasks feed",
        "Rebuild the onboarding flow with the new tokens",
        "Fix jank on the activity list at 120Hz",
        "Add biometric unlock behind a settings toggle",
        "Ship push notification deep links",
        "Reduce cold start below 1.2s on mid-tier Android",
        "Localise strings for FR, DE and JA",
        "Wire crash reporting to the release dashboard",
    ],
    "Design System 2.0": [
        "Define semantic colour tokens for light and dark",
        "Audit focus rings against WCAG 2.2",
        "Replace the legacy Modal with the Dialog primitive",
        "Publish the icon set as a versioned package",
        "Write migration codemods for Button props",
        "Add visual regression snapshots to CI",
    ],
    "Billing & Invoicing": [
        "Model usage metering events",
        "Choose the tax calculation provider",
        "Draft the dunning email sequence",
        "Spec the self-serve invoice portal",
        "Map proration rules for mid-cycle upgrades",
        "Review PCI scope with the security team",
    ],
    "Data Warehouse Migration": [
        "Inventory reporting queries hitting the primary DB",
        "Prototype CDC replication into the warehouse",
        "Define the dimensional model for revenue reporting",
        "Estimate storage and compute costs for a year",
        "Plan the read-only cutover window",
    ],
    "Q2 Compliance Audit": [
        "Collect access review evidence for Q2",
        "Remediate the stale service account finding",
        "Update the incident response policy",
        "Run the tabletop disaster-recovery exercise",
        "Close out auditor follow-up questions",
    ],
    "Legacy CRM Sunset": [
        "Export historical accounts to cold storage",
        "Redirect legacy CRM URLs to the new app",
        "Cancel the legacy vendor contract",
    ],
    "Incident Response": [
        "Publish the sev-1 escalation runbook",
        "Automate status page updates from alerts",
        "Rotate the on-call schedule for next quarter",
        "Write the post-incident review for INC-482",
        "Add synthetic checks for the checkout path",
    ],
    "Vendor Onboarding": [
        "Draft the security questionnaire",
        "Standardise the MSA template",
        "Build the procurement approval checklist",
    ],
    "Warehouse Automation": [
        "Evaluate handheld scanner vendors",
        "Model the pick-path optimisation algorithm",
        "Scope the WMS integration",
    ],
    "Client Portal MVP": [
        "Design the milestone timeline view",
        "Implement document sign-off",
        "Add per-client branding options",
        "Scope the read-only permission model",
    ],
    "Brand Refresh": [
        "Shortlist three logotype directions",
        "Define the marketing colour palette",
    ],
}

TASK_LABELS = [
    "backend",
    "frontend",
    "infra",
    "design",
    "security",
    "bug",
    "tech-debt",
    "research",
    "docs",
    "customer",
    "performance",
    "accessibility",
]

TASK_DESCRIPTIONS = [
    "### Context\n\n{title}. Raised during the weekly planning review after the "
    "last customer escalation.\n\n### Acceptance criteria\n\n- Behaviour is "
    "covered by tests\n- No regression in p95 latency\n- Documented in the "
    "team handbook\n",
    "Follow-up from the architecture review. Scope is deliberately narrow: "
    "{title}, nothing adjacent. If the change grows past a day, split it and "
    "link the follow-up here.",
    "**Why now:** this blocks two downstream tickets and the customer pilot "
    "starting next month.\n\n**Risk:** medium — touches shared code paths, so "
    "roll out behind a flag.",
    "",  # deliberately empty: exercises the empty-state rendering
]


# ---------------------------------------------------------------------------
# Documents — (filename, title, description, body)
# Mixed extensions on purpose: .md/.txt extract cleanly, .csv is unsupported by
# the extractor so its embedding job lands in a "failed/skipped" state.
# ---------------------------------------------------------------------------
DOCUMENTS = [
    (
        "engineering-onboarding.md",
        "Engineering Onboarding Guide",
        "Everything a new engineer needs in their first two weeks.",
        """# Engineering Onboarding

Welcome to Aurora Labs. This guide covers your first two weeks.

## Day one

Get access to the identity provider, the code host and the observability stack.
Your buddy will pair with you on a starter ticket the same afternoon — we
believe the fastest way to learn a codebase is to change it.

## Development environment

The platform runs on PostgreSQL 16 with the pgvector extension enabled. The API
is Django 5 with Django REST Framework; the web client is Next.js with the App
Router. Run the API on port 8000 and the web client on port 3000. Seed data is
available through the seed_demo management command.

## How we work

Work is tracked as tasks inside a project. Every task has an assignee, a
priority and — where it matters — a due date. When you go on leave or move
teams, you file a handover so the person picking the work up gets your summary,
the pending items and the resources they will need. A manager reviews it.

## Code review

Two approvals for anything touching authentication, billing or the tenancy
boundary. One approval otherwise. Reviews are expected within one business day;
if you cannot get to it, say so in the thread rather than leaving it silent.

## Incidents

Sev-1 pages the on-call engineer immediately. Declare early — an incident that
turns out to be minor costs far less than one declared an hour late. Write the
post-incident review within three working days, blameless, focused on the
system rather than the person.
""",
    ),
    (
        "atlas-architecture-decision-record.md",
        "ADR-014: Atlas Service Boundaries",
        "Why we split billing and identity out of the monolith first.",
        """# ADR-014: Atlas service boundaries

**Status:** accepted · **Date:** this quarter · **Deciders:** platform guild

## Context

The Atlas monolith couples billing, identity and the core workflow engine in a
single deployable. Release cadence is limited by the slowest test suite, and a
billing regression can take the whole product down.

## Decision

Extract billing and identity first. Both have clear data ownership, a small
number of inbound call sites and independent scaling profiles. The workflow
engine stays in the monolith for now — its data model is entangled with almost
every table and extracting it early would force distributed transactions.

## Consequences

Positive: independent deploys for the two highest-risk domains, smaller blast
radius, and a forcing function for real API contracts.

Negative: two more services to operate, cross-service reads that used to be
joins, and a migration window where both code paths must be maintained.

## Rollout

Traffic moves behind the atlas-read flag, one percent at a time, with automated
rollback on error-rate regression. Contract tests run on every pull request in
both repositories.
""",
    ),
    (
        "incident-response-runbook.md",
        "Incident Response Runbook",
        "Severity definitions, escalation path and comms templates.",
        """# Incident response runbook

## Severity levels

**Sev-1** — customer-facing outage or data loss risk. Page immediately, open a
bridge, post to the status page within fifteen minutes.

**Sev-2** — major degradation with a workaround. Page during business hours,
update stakeholders hourly.

**Sev-3** — minor or internal-only impact. Handle in the normal queue.

## Roles

The incident commander owns decisions and is explicitly not debugging. The
communications lead owns the status page and stakeholder updates. The operations
lead drives mitigation. On small incidents one person may hold two roles, but
never all three.

## First fifteen minutes

Confirm the impact, declare the severity, assign the roles, and mitigate before
diagnosing. Rolling back a deploy is almost always faster than understanding it.

## After the incident

Write the review within three working days. Include the timeline, the
contributing factors, what made detection slow, and the specific follow-up
actions with owners and dates. Actions without an owner are not actions.
""",
    ),
    (
        "handover-policy.md",
        "Task Handover Policy",
        "What a good handover contains and how review works.",
        """# Task handover policy

A handover is a formal transfer of a task from one person to another. It exists
so context does not evaporate when someone changes teams, goes on leave, or
finishes a rotation.

## What to include

**Summary** — the state of the work in plain language: what is done, what was
tried and abandoned, and why the current approach was chosen.

**Pending items** — the concrete remaining steps, ordered. "Finish the API" is
not a pending item; "add pagination to GET /invoices and update the client hook"
is.

**Resources** — links to branches, design files, dashboards, credentials
requests and the people who know the surrounding systems.

## Review

A manager, admin or workspace owner reviews every handover. Approving reassigns
the task to the recipient. Rejecting returns it with a comment explaining what
is missing — usually pending items that are too vague to action.

Handovers are exportable as PDF for records and for teams that need a signed
artefact at the end of a contract.
""",
    ),
    (
        "q2-compliance-summary.md",
        "Q2 Compliance Audit Summary",
        "Scope, findings and remediation status for the Q2 SOC 2 audit.",
        """# Q2 compliance audit summary

## Scope

Security, availability and confidentiality criteria across the platform,
covering the production environment and the supporting corporate systems.

## Findings

One moderate finding: a service account retained write access to the reporting
database after the owning system was decommissioned. Access was revoked the same
day it was identified, and quarterly access reviews now cover service accounts
explicitly, not just human users.

Two observations: our offboarding checklist did not include the analytics tool,
and change tickets occasionally lacked a documented rollback plan. Both were
closed with process changes.

## Evidence

Access reviews, change management records, incident reviews, vendor risk
assessments and the disaster recovery test report. All evidence lives in the
compliance workspace and is retained for three years.

## Next audit

Fieldwork begins in the first month of the next quarter. Evidence collection is
continuous rather than a scramble in the final two weeks.
""",
    ),
    (
        "mobile-v3-research-notes.txt",
        "Mobile v3 User Research Notes",
        "Raw notes from twelve customer interviews on the v3 beta.",
        """Mobile v3 research notes

Twelve interviews, mixed segments, thirty to forty minutes each.

Offline behaviour dominated the feedback. Field users open the app in places
with no signal and expect the last synced state to be there. Eight of twelve
described a workaround involving screenshots. Any conflict resolution that
silently discards their edit will be read as data loss, regardless of what
actually happened on the server.

Notifications were the second theme. Deep links that drop the user on a list
screen instead of the item they tapped were called out repeatedly. Five people
had disabled notifications entirely because of it.

Cold start matters more than raw scrolling performance. Several users open the
app for under ten seconds at a time; a two second launch is a meaningful share
of the whole session.

Least important: theming and customisation. Nobody raised it unprompted.

Recommended order: offline sync correctness, notification deep links, cold start
budget, then everything else.
""",
    ),
    (
        "release-checklist.md",
        "Release Checklist",
        "Pre-flight, deploy and post-deploy steps for a production release.",
        """# Release checklist

## Pre-flight

Migrations reviewed and reversible. Feature flags default to off. Changelog
entry written for anything customer visible. On-call engineer is aware the
release is going out and is not simultaneously handling an incident.

## Deploy

Ship migrations first, then application code, so the running version tolerates
both schema states. Watch error rate and p95 latency for ten minutes before
declaring the deploy healthy.

## Post-deploy

Enable flags gradually — one percent, then ten, then fifty, then everyone —
with at least thirty minutes between steps for anything touching billing or
authentication. Update the release dashboard and close the ticket with the
deployed version.

## Rollback

If error rate exceeds the baseline by more than half a percentage point, roll
back first and investigate afterwards. Rolling back is never a failure; a long
debugging session with customers impacted is.
""",
    ),
    (
        "team-directory.csv",
        "Team Directory (Q3)",
        "Contact sheet — unsupported file type, kept to test the skip path.",
        """name,role,team,timezone
Maya Chen,Engineering Manager,Platform,UTC+1
Omar Haddad,Staff Engineer,Platform,UTC+2
Priya Nair,Product Manager,Mobile,UTC+5:30
Liam Novak,Senior Engineer,Mobile,UTC+1
Sofia Reyes,Engineer,Design Systems,UTC-5
Tom Okafor,Engineer,Billing,UTC
Ines Dubois,Designer,Design Systems,UTC+1
Rahul Mehta,Data Engineer,Platform,UTC+5:30
Yuki Tanaka,Engineer,Mobile,UTC+9
""",
    ),
]

NORTHWIND_DOCUMENTS = [
    (
        "on-call-rotation.md",
        "On-call Rotation & Expectations",
        "Who carries the pager, when, and what is expected of them.",
        """# On-call rotation

One primary and one secondary, rotating weekly, handover on Monday morning.

The primary acknowledges pages within five minutes during business hours and
fifteen minutes overnight. The secondary exists so that a missed page has a
backstop, not so that the primary can ignore the pager.

Anything that pages twice in a week without a fix gets a ticket in the next
planning session. Alert fatigue is a reliability problem, not a personal one.

Compensation follows the standard on-call policy. If you are paged overnight,
take the following morning off — this is expected, not a favour.
""",
    ),
    (
        "vendor-security-questionnaire.md",
        "Vendor Security Questionnaire",
        "Baseline questions every new vendor must answer before contracting.",
        """# Vendor security questionnaire

Data handling: what customer data is processed, where is it stored, and how long
is it retained after termination?

Access control: is SSO with SAML or OIDC supported? Is multi-factor
authentication enforced for administrative accounts?

Assurance: is there a current SOC 2 Type II or ISO 27001 report? When was the
last penetration test, and can a summary be shared?

Incident handling: what is the notification window for a breach affecting our
data, and to which contact?

Subprocessors: list them, with the notification process for changes.

Any "no" answer is not automatically disqualifying, but it must be recorded with
a compensating control before the contract is signed.
""",
    ),
]

PORTAL_DOCUMENTS = [
    (
        "client-portal-scope.md",
        "Client Portal MVP Scope",
        "What is in and explicitly out of the first portal release.",
        """# Client portal MVP scope

## In scope

Milestone timeline with status, document list with download, deliverable
sign-off with an audit trail, and per-client branding limited to a logo and an
accent colour.

## Out of scope

Client-authored comments, file uploads from the client side, invoicing, and any
write access to tasks. Read-only is the whole point of the MVP: it removes an
entire class of permission bugs from the first release.

## Open questions

Do clients need per-user accounts or one shared login per organisation? Legal
prefers per-user for the audit trail; two pilot clients have asked for shared
access. Current plan is per-user with an easy invite flow.
""",
    ),
]


# ---------------------------------------------------------------------------
# Handovers — (summary, pending_items, resources)
# ---------------------------------------------------------------------------
HANDOVER_CONTENT = [
    (
        "Picking up the billing extraction while I'm on parental leave. The "
        "service boundary is agreed (see ADR-014) and the read path is already "
        "behind the atlas-read flag at 5% traffic. The write path is untouched.",
        "1. Raise the read flag to 25% and watch error rate for a day\n"
        "2. Port the invoice PDF endpoint — it still calls the monolith directly\n"
        "3. Delete the shadow-write comparison job once parity holds for a week",
        "Branch: feature/atlas-billing-read\n"
        "Dashboard: Grafana > Atlas > Billing read path\n"
        "Ask Omar about the proration edge cases — he wrote the original rules.",
    ),
    (
        "Handing over the offline sync work as I rotate to the platform team. "
        "Conflict resolution is implemented for tasks; documents still use "
        "last-write-wins, which research says users will read as data loss.",
        "1. Replace last-write-wins on documents with the merge dialog\n"
        "2. Add a sync-status indicator to the app bar\n"
        "3. Write the migration for the local database schema bump",
        "Design file: Mobile v3 > Sync states\n"
        "Research notes are in the workspace documents.\n"
        "Yuki has context on the Android background execution limits.",
    ),
    (
        "Transferring the design system migration. Tokens are published and "
        "Button/Input/Dialog are migrated; roughly forty call sites still use "
        "the legacy Modal.",
        "1. Run the Button codemod across the marketing site\n"
        "2. Migrate the remaining Modal call sites\n"
        "3. Turn on visual regression checks in CI once the noise settles",
        "Package: @aurora/design-system@2.0.0-rc.4\n"
        "Codemods live in tools/codemods.\n"
        "Ines owns the accessibility audit checklist.",
    ),
    (
        "Rotating off the compliance evidence collection. Q2 is closed with one "
        "moderate finding remediated; the continuous evidence pipeline is half "
        "built.",
        "1. Automate the quarterly access review export\n"
        "2. Add service accounts to the offboarding checklist\n"
        "3. Schedule the next tabletop exercise",
        "Evidence lives in the compliance workspace.\n"
        "Auditor contact is in the shared vendor sheet.",
    ),
    (
        "Passing on the warehouse migration prototype before it goes on hold. "
        "CDC replication works end to end in staging; nothing is in production.",
        "1. Document the staging setup before it is torn down\n"
        "2. Capture the cost estimate in the project description\n"
        "3. Re-open when the Q3 infrastructure budget lands",
        "Prototype branch: spike/warehouse-cdc\n"
        "Cost model spreadsheet is linked in the project description.",
    ),
    (
        "Taking the incident runbook work off my plate — I'm moving to the "
        "mobile team. The runbook is published; automation is not started.",
        "1. Wire status page updates to alert webhooks\n"
        "2. Add synthetic checks for checkout\n"
        "3. Run a dry-run drill with the new escalation path",
        "Runbook is in workspace documents.\n"
        "Status page API token is in the ops vault.",
    ),
    (
        "Handover of the vendor onboarding checklist. Questionnaire is drafted "
        "and legal has reviewed the MSA template.",
        "1. Get security sign-off on the questionnaire\n"
        "2. Publish the procurement checklist to the handbook",
        "Draft questionnaire is in workspace documents.",
    ),
    (
        "Client portal sign-off flow — handing over while I'm on rotation. The "
        "read-only permission model is scoped but not implemented.",
        "1. Implement per-user client accounts\n"
        "2. Build the sign-off audit trail\n"
        "3. Confirm branding scope with the two pilot clients",
        "Scope doc is in workspace documents.\n"
        "Pilot client contacts are with Priya.",
    ),
]

REVIEW_COMMENTS_APPROVED = [
    "Clear summary and the pending items are actionable. Approved — reassigned.",
    "Good handover. Confirmed the recipient has access to the branch and the "
    "dashboard. Approved.",
    "Approved. Please add the rollback note to the runbook when you get a "
    "chance, but that shouldn't block the transfer.",
]

REVIEW_COMMENTS_REJECTED = [
    "Pending items are too vague to action — 'finish the API' could be a day or "
    "a month. Please break them down and resubmit.",
    "Missing the resources section entirely: no branch, no dashboard, no "
    "contact for the tricky parts. Resubmit with those and I'll approve.",
]


# ---------------------------------------------------------------------------
# Comments. "{m}" is replaced with an @mention token by the seeder.
# ---------------------------------------------------------------------------
COMMENT_SEEDS = [
    "{m} could you take a look at this before Thursday? It blocks the pilot.",
    "Tried the flag-based rollout on staging and it held at 3x peak. Numbers are "
    "in the dashboard.",
    "This overlaps with the work {m} is doing on the sync engine — worth a "
    "fifteen minute call rather than a comment thread.",
    "Scope check: are we doing the migration in this ticket or splitting it? I'd "
    "vote split.",
    "Blocked on the vendor response. Chased them again today; will escalate on "
    "Monday if nothing lands.",
    "Fixed in the latest push. Left the old code path behind the flag for one "
    "release so we can roll back cleanly.",
    "The acceptance criteria don't mention the accessibility audit — {m}, is "
    "that intentional?",
    "Nice work on this one. The p95 dropped from 480ms to 190ms.",
]

COMMENT_REPLIES = [
    "Yes — deliberately out of scope here, it's tracked separately.",
    "Agreed, splitting it. I'll link the follow-up once it exists.",
    "Booked a call for tomorrow morning.",
    "Confirmed, thanks for checking.",
    "Escalated. Vendor says end of week.",
]


# ---------------------------------------------------------------------------
# AI assistant content
# ---------------------------------------------------------------------------
AI_CONVERSATIONS = [
    (
        "What does a good handover look like?",
        [
            ("user", "What does a good handover look like here?"),
            (
                "assistant",
                "A handover has three parts. The **summary** describes the state "
                "of the work in plain language, including approaches that were "
                "tried and abandoned. **Pending items** are concrete, ordered "
                "steps — the policy explicitly calls out that \"finish the API\" "
                "is not a pending item. **Resources** covers branches, "
                "dashboards, design files and the people who know the "
                "surrounding systems.\n\nA manager, admin or workspace owner "
                "reviews every handover. Approving reassigns the task; "
                "rejecting returns it with a comment.",
            ),
            ("user", "Who can review one?"),
            (
                "assistant",
                "Workspace owners, admins and managers. Members can submit "
                "handovers but not review them.",
            ),
        ],
    ),
    (
        "Why did we split billing out first?",
        [
            ("user", "Why did we extract billing before the workflow engine?"),
            (
                "assistant",
                "ADR-014 gives two reasons. Billing and identity have clear data "
                "ownership and few inbound call sites, so the extraction is "
                "tractable. The workflow engine's data model is entangled with "
                "nearly every table, so extracting it early would have forced "
                "distributed transactions.\n\nThe tradeoff accepted was two more "
                "services to operate and cross-service reads replacing joins.",
            ),
        ],
    ),
    (
        "Incident severity levels",
        [
            (
                "system",
                "You are the Aurora Labs workspace assistant. Answer from the "
                "workspace documents and cite them.",
            ),
            ("user", "When do I declare a sev-1?"),
            (
                "assistant",
                "Sev-1 is a customer-facing outage or a data-loss risk: page "
                "immediately, open a bridge, and post to the status page within "
                "fifteen minutes. The runbook is explicit that declaring early "
                "is cheap and declaring late is expensive — an incident that "
                "turns out minor costs far less than one declared an hour in.",
            ),
            ("user", "And who runs it?"),
            (
                "assistant",
                "Three roles: incident commander (decisions, explicitly not "
                "debugging), communications lead (status page and stakeholders), "
                "and operations lead (mitigation). One person can hold two roles "
                "on a small incident, never all three.",
            ),
        ],
    ),
    (
        "Mobile v3 priorities from research",
        [
            ("user", "What did the v3 research say we should prioritise?"),
            (
                "assistant",
                "The recommended order was: offline sync correctness, "
                "notification deep links, cold start budget, then everything "
                "else. Offline behaviour dominated — eight of twelve "
                "interviewees described a screenshot workaround, and the notes "
                "warn that silently discarding an edit will be read as data "
                "loss. Theming was raised by nobody unprompted.",
            ),
        ],
    ),
    (
        "Release rollback threshold",
        [
            ("user", "At what point do we roll back a release?"),
            (
                "assistant",
                "When error rate exceeds baseline by more than half a percentage "
                "point. The checklist is direct about it: roll back first, "
                "investigate afterwards.",
            ),
        ],
    ),
]

AI_SEARCH_QUERIES = [
    "handover review process",
    "who reviews handovers",
    "atlas service boundaries",
    "rollback threshold",
    "sev-1 definition",
    "offline sync conflict",
    "access review evidence",
    "on-call expectations",
    "vendor security questionnaire",
    "feature flag rollout steps",
    "cold start budget mobile",
    "post incident review timeline",
]

PROMPT_TEMPLATES = [
    (
        "Summarise a handover",
        "engineering",
        "Condense a handover into a five-line brief for the recipient.",
        "Summarise the following handover for the person picking the work up. "
        "Five lines maximum: current state, the single most important pending "
        "item, the biggest risk, who to ask, and where the code lives.\n\n"
        "{{handover}}",
        True,
    ),
    (
        "Draft a post-incident review",
        "engineering",
        "Turn a raw incident timeline into a blameless review.",
        "Write a blameless post-incident review from this timeline. Include: "
        "impact, timeline, contributing factors, what made detection slow, and "
        "follow-up actions with an owner each. Never attribute cause to a "
        "person.\n\n{{timeline}}",
        True,
    ),
    (
        "Weekly status update",
        "management",
        "Turn the week's task activity into a stakeholder update.",
        "Write a weekly status update for {{project}}. Sections: shipped, in "
        "flight, blocked, and what we need from stakeholders. Keep it under 200 "
        "words and avoid engineering jargon.",
        True,
    ),
    (
        "Break down a task",
        "planning",
        "Split a large task into actionable subtasks.",
        "Break the following task into subtasks that can each be finished in "
        "under a day. For each, give a title, an estimate in hours and any "
        "dependency on another subtask.\n\n{{task}}",
        True,
    ),
    (
        "Review acceptance criteria",
        "planning",
        "Check whether a ticket is actually actionable.",
        "Review these acceptance criteria. Flag anything ambiguous, unmeasurable "
        "or missing (rollback, telemetry, accessibility, error states). Suggest "
        "a rewrite for each problem you find.\n\n{{criteria}}",
        False,
    ),
    (
        "Explain this document to a new joiner",
        "onboarding",
        "Rewrite an internal document for someone in their first week.",
        "Explain the attached document to someone who joined this week. Expand "
        "every internal acronym, state assumptions the document leaves implicit, "
        "and end with the three things they should remember.\n\n{{document}}",
        True,
    ),
    (
        "Vendor risk summary",
        "security",
        "Summarise a vendor questionnaire response into a risk verdict.",
        "Summarise this vendor questionnaire response. List each 'no' answer "
        "with the compensating control, then give an overall verdict: approve, "
        "approve with conditions, or reject.\n\n{{response}}",
        True,
    ),
    (
        "Customer-facing changelog entry",
        "general",
        "Turn a merged change into customer-readable release notes.",
        "Write a changelog entry for this change. One sentence on what changed, "
        "one on why it matters to the customer. No internal service names.\n\n"
        "{{change}}",
        True,
    ),
    (
        "Meeting notes to actions",
        "general",
        "Extract owned, dated actions from messy notes.",
        "Extract the action items from these meeting notes. Each needs an owner "
        "and a date. List anything that was discussed but left unowned "
        "separately under 'unowned'.\n\n{{notes}}",
        False,
    ),
]


# ---------------------------------------------------------------------------
# Notifications — (type, title, message) for the explicitly seeded ones.
# ---------------------------------------------------------------------------
SYSTEM_NOTIFICATIONS = [
    (
        "system",
        "Scheduled maintenance on Sunday",
        "The API will be read-only between 02:00 and 03:00 UTC while we run the "
        "storage upgrade.",
    ),
    (
        "system",
        "Your workspace passed its Q2 audit",
        "Zero major findings. The evidence pack is attached to the compliance "
        "project.",
    ),
]
