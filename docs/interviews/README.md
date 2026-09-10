# Interview Preparation

[← Docs index](../README.md)

Every question here is derived from **this codebase**. No generic
"what is a closure" filler.

---

## Files

| File | Contents |
|---|---|
| [project-explanation.md](project-explanation.md) | 30-second, 1-minute, 3-minute and 5-minute versions of "tell me about your project" |
| [memorize.md](memorize.md) | The facts you must know cold |
| [whiteboard.md](whiteboard.md) | How to draw this system live |
| [code-walkthrough.md](code-walkthrough.md) | The 12 files an interviewer may ask you to open, and what to say |
| [beginner-questions.md](beginner-questions.md) | 30 questions |
| [intermediate-questions.md](intermediate-questions.md) | 30 questions |
| [advanced-questions.md](advanced-questions.md) | 30 questions |
| [senior-architect-questions.md](senior-architect-questions.md) | 20 architect-level questions |
| [frontend-questions.md](frontend-questions.md) | 20 |
| [backend-questions.md](backend-questions.md) | 20 |
| [database-questions.md](database-questions.md) | 20 |
| [security-questions.md](security-questions.md) | 20 |
| [scenario-questions.md](scenario-questions.md) | 20 "what would you do if…" |
| [debugging-questions.md](debugging-questions.md) | 20 debugging scenarios with structured answers |
| [why-did-you-do-this.md](why-did-you-do-this.md) | Defending every major decision |
| [difficult-followups.md](difficult-followups.md) | Follow-up chains that go three or four levels deep |

**Total: 210+ questions.**

---

## How to use this

**One week out** — read the core docs
([02](../02-system-architecture.md), [08](../08-authentication-authorization.md),
[11](../11-data-flow.md)), then work through beginner → intermediate → advanced.

**Two days out** — [project-explanation.md](project-explanation.md) until the
3-minute version is fluent, then [difficult-followups.md](difficult-followups.md)
and [25-known-limitations.md](../25-known-limitations.md).

**Morning of** — [memorize.md](memorize.md) and
[whiteboard.md](whiteboard.md). Nothing else.

---

## Three principles for answering well

### 1. Name the file

"Tenant isolation is enforced in `WorkspaceScopedViewSet.get_queryset()` in
`apps/common/viewsets.py`" beats "I filter by workspace." Specifics prove you
built it.

### 2. Volunteer the trade-off

Every decision cost something. Saying so unprompted is the single strongest
signal you can send:

> "I put the tokens in cookies rather than localStorage so the Next.js edge
> middleware could read them. The cost is that they're not httpOnly, so an XSS
> would expose both. If I were hardening this for production, the refresh token
> would move to an httpOnly cookie set by the backend and the access token would
> live in memory — which also removes the reason the middleware needed to read
> them at all."

That is a better answer than any defence of the current design.

### 3. Know your own bugs

An interviewer who reads the code **will** find something. Getting there first
turns a weakness into evidence of judgement. The five worth having ready:

| Issue | One-line framing |
|---|---|
| Non-httpOnly tokens | "A conscious trade-off for the edge guard; documented in the file. Here's the fix." |
| No `completed_at` | "Analytics infers the completion week from `updated_at`. I noted it in the view docstring rather than hiding it." |
| Document list N+1 | "Two `SerializerMethodField`s hit the database per row. `annotate` plus a `Prefetch` takes 41 queries to 3." |
| Empty test files for tasks and projects | "I tested the risky parts — auth, roles, the handover workflow. CRUD is only covered by the smoke test. Tasks should have their own file." |
| Two pending handovers per task | "There's no constraint preventing it. It's the first business rule I'd add." |

---

## The 10 questions most likely to be asked

1. Walk me through your architecture. → [whiteboard.md](whiteboard.md)
2. How does authentication work, end to end? → [08](../08-authentication-authorization.md)
3. How do you stop one customer seeing another's data? → [security-questions.md](security-questions.md)
4. Explain your database design. → [database-questions.md](database-questions.md)
5. What's the most complex thing you built? → the handover workflow, or the RAG pipeline
6. What would you do differently? → [25](../25-known-limitations.md)
7. How does the AI part actually work? → [modules/ai-assistant.md](../modules/ai-assistant.md)
8. How would you scale this? → [19](../19-performance-scalability.md)
9. Why Django and not Node? → [why-did-you-do-this.md](why-did-you-do-this.md)
10. Walk me through one feature end to end. → the handover, from
    [11](../11-data-flow.md#flow-3--submitting-and-approving-a-handover-)

---

## Your three strongest talking points

Lead with these. They are genuinely good engineering and they are all defensible
in detail.

**1. Multi-tenancy enforced structurally, not by discipline.**
`WorkspaceScopedViewSet` makes the safe path the default. Four independent
barriers: the base queryset, the create check, the AI gate, the vector-search
filter. Cross-tenant reads return 404, not 403, so the API never confirms an id
exists.

**2. The system degrades instead of failing.**
Redis down → in-process channel layer and inline tasks. Broker down → tasks run
inline. Websocket down → polling. LLM down → 502 with the provider's message.
pgvector missing → a clean 503 with setup instructions. SMTP down → logged and
retried. **PostgreSQL is the only hard dependency**, and local development needs
nothing else.

**3. The AI writes nothing.**
Retrieval is workspace-filtered before the tenant boundary can be crossed.
Retrieved content is fenced as untrusted with explicit guardrails. Generated
tasks are returned for review and created through the normal Task API, with the
same validation as a manual one. The model has no tools.
