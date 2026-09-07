# Brisken web estate: ownership + transfer runbook

Status: draft for owner review. Not sent to Dirk.
Prepared: 2026-09-07. Every ownership fact below was verified live on that
date by API or CLI call; the method is named per row so it can be re-checked.

## 1. Why this exists

Every Brisken web property we built is currently hosted, billed and
administered under Matthias's personal accounts. That includes
**brisken.com itself**, Brisken's live corporate website. If those accounts
lapse, are suspended, or simply lose their operator, Brisken has no
administrative path back to their own site.

This is worth fixing on its own merits, independent of any departure
timeline. The transfer below is the fix.

## 2. What Brisken already owns (no action needed)

Verified 2026-09-07. These are the pieces that are already safe.

| Asset | Evidence |
|---|---|
| `brisken.com` domain + DNS | RDAP: registered at GoDaddy 2009-10-01, expiry 2028-10-01, NS `pdns01/pdns02.domaincontrol.com`. Our GoDaddy API key returns 401 against it, so the registrar account is Brisken's, not ours. |
| Entra app "BRISKEN MARKETING OPS INTEGRATION" | Registered in Brisken tenant `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`. Brisken IT can revoke or reissue at will. |
| OpenAI API key running expense-recon | Dirk's own key (`OPENAI_API_KEY` on the Fly app). |
| Zoho CRM / Books | Brisken's tenant; we hold read-only OAuth credentials against it. |

This matters more than it looks. Because Brisken controls DNS, no scenario
locks them out permanently: worst case they repoint `brisken.com` at new
hosting and lose only the content, which is in git. The transfer is about
avoiding that fire drill, not about preventing a hostage situation.

## 3. What we own that has to move

### Vercel (account `matthias-5647` / neumath4@icloud.com, team `matthias-neumanns-projects`, id `team_MNNYUo2DofKqKUISX0X01rre`)

Verified via `api.vercel.com/v9/projects` + `/domains` with the Brisken token.

| Project | Project id | Domains served |
|---|---|---|
| `brisken-onepilot` | `prj_Avie4cXev9Axx4WfKNAJfob3FEap` | `brisken.com`, `www.brisken.com`, `onepilot.brisken.com` |
| `resources-site` | `prj_9EDCYbR0tJV7dwe8aC6HxbQYpuH9` | `resources.brisken.com` |
| `brisken-rome-hub` | `prj_EFYtjsRojr7xHONB9w4UhZg5JOAu` | `rome2026.brisken.com` |

The same team also holds `unpauseai-web`, `one-assessment-demo` and
`cv-generator`, which are ours and stay. So this is a **per-project
transfer**, never a team handover.

`brisken-onepilot` additionally carries a **Neon Postgres** database wired
through the Vercel storage integration (18 `DATABASE_*` env vars including
`DATABASE_NEON_PROJECT_ID`), backing `/api/book-demo` lead capture, plus
`NOTIFY_WEBHOOK_URL`. Storage integrations are provisioned to the owning
team, so this does not ride along with a project transfer. See 4.2.

### Fly.io (org `personal`, "Matthias Neum", account matneumann07@gmail.com)

`flyctl orgs list` confirms exactly one org. There is no Brisken org.

| App | State | Persistent data |
|---|---|---|
| `brisken-expense-recon` | suspended / scale-to-zero | volume `recon_data` 1GB fra: SQLite ledger, receipts, cross-run memory. Criss's financial records. |
| `brisken-lead-desk` | deployed | volume `lead_desk_data` 1GB fra: contacts + outreach events. Lead PII. |
| `brisken-onepilot` | suspended | none |
| `brisken-onepilot-proto` | suspended | volume `onepilot_data`: review feedback JSONL |

Both data volumes hold material Brisken owns and we merely host.

### GitHub (`011matthias`, no orgs)

| Repo | Role |
|---|---|
| `011matthias/brisken-expense-review` (private) | The expense-recon React SPA. Two-way synced with Lovable. |
| `011matthias/agentic-ops1.01` | Our monorepo. Brisken code lives under `workspace/clients/brisken/`; this repo does **not** transfer. Brisken's code reaches them via the existing subtree-push handoff pattern. |

### Lovable

Project `brisken-reconcile-dash.lovable.app`, connected to
`brisken-expense-review`, on Matthias's Lovable seat. Publishing is a
dashboard action with no API, so whoever holds the seat is the only person
who can ship a frontend change.

## 4. Transfer plan

Order matters: lowest blast radius first, brisken.com last, once the
mechanics are proven on a site nobody would notice breaking.

### 4.0 Prerequisites (Brisken side, one time)

1. Vercel team on a paid plan, owned by a Brisken admin account. Custom
   domains on a personal Hobby account violate Vercel's commercial-use
   terms, so this has to be a team, not a personal account.
2. Fly.io organization, created by a Brisken account, with billing attached.
3. GitHub organization, with a Brisken-owned admin.
4. Lovable seat, if Brisken wants to keep editing the SPA visually.
5. A Neon account, or acceptance that lead capture moves to their Vercel
   team's own storage integration.

### 4.1 Vercel projects (rehearse on `brisken-rome-hub`)

Per project: Settings, Transfer Project, target the Brisken team. Custom
domains have to be re-verified in the receiving account, normally via a
TXT record. Brisken controls GoDaddy DNS, so they add it themselves.

Expected downtime: none for `*.vercel.app`, brief for a custom domain
during re-verification. Rehearsing on `rome2026` first tells us the real
number before we touch the apex.

Sequence: `brisken-rome-hub`, then `resources-site`, then
`brisken-onepilot`.

Carry over per project: env vars are not guaranteed to follow a transfer.
Export names and values first (`vercel env pull`, or the API), re-add on
the receiving side, redeploy, then verify the deployed origin per the
deploy verification gate.

### 4.2 Neon (the one genuine migration, not a transfer)

The lead-capture DB is a Vercel-managed Neon integration on our team. Plan:

1. Dump the leads table from the current Neon project.
2. Brisken's Vercel team provisions its own Neon integration on the
   transferred `brisken-onepilot` project, which injects a fresh
   `DATABASE_*` set.
3. Restore the dump, redeploy, then submit a real test through
   `brisken.com/demo` and confirm the row lands.
4. Only then decommission the old Neon project.

Do not treat step 2 as done until step 3's row is visible. A demo form that
silently stops persisting looks identical to a quiet week.

### 4.3 Fly apps

`flyctl apps move <app> --org <brisken-org>` is the intended path and
volumes are app-scoped, so they follow the app. UNVERIFIED on this estate:
we have never run it here.

Fallback if the move misbehaves, and the safer option for the two apps
holding real data: create the app fresh in the Brisken org, copy the volume
contents off the old volume with `flyctl sftp` (the documented testing-loop
pattern), deploy, re-set secrets, cut over, keep the old app suspended for a
rollback window rather than deleting it.

Secrets to re-create on the receiving side, values not in git:

- `brisken-expense-recon`: `EXPENSE_RECON_AUTH_SECRET`,
  `EXPENSE_RECON_OPERATOR_CODE`, `EXPENSE_RECON_OPERATOR_CODES`,
  `EXPENSE_RECON_RECEIPT_FIRST`, `EXPENSE_RECON_AUTO_MATERIALIZE`,
  `OPENAI_API_KEY`, `BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`,
  `BRISKEN_GRAPH_CLIENT_SECRET`
- `brisken-lead-desk`: `LEAD_DESK_AUTH_SECRET`, `LEAD_DESK_INGEST_SECRET`,
  `LEAD_DESK_WORKER_SECRET`, `LEAD_DESK_AUTH_EMAILS`, `LEAD_DESK_BASE_URL`,
  `BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`, `BRISKEN_GRAPH_CLIENT_SECRET`
- `brisken-onepilot-proto`: `BRISKEN_SITE_AUTH_SECRET`

Rotating the auth secrets during the move invalidates existing sign-in
cookies. That is the right moment to do it, since it also cuts our access
cleanly, but tell Criss and Dirk before it happens so a forced re-login is
expected rather than alarming.

The Graph client secret is Brisken's to reissue in their own tenant. Doing
that as part of the cutover means our copy stops working, which is the
point.

### 4.4 GitHub + Lovable

1. Transfer `011matthias/brisken-expense-review` to the Brisken org
   (Settings, Transfer ownership). Redirects keep old clone URLs working,
   but do not rely on them.
2. Reconnect the Lovable project to the repo at its new path. The Lovable
   GitHub App authorization is per-account, so expect to re-authorize.
   UNVERIFIED: whether Lovable supports transferring a project between
   accounts directly. Fallback: Brisken creates the Lovable project and
   connects it to the transferred repo, which is the same end state.
3. Verify with a structural DOM probe against the published origin, not a
   merge or a label check. A Lovable merge is not a publish.

### 4.5 Documentation Brisken needs to operate it

Not optional; without it the transfer hands over control they cannot use.

- How to deploy each surface, including that Lovable publish is a manual
  dashboard click nobody is notified about.
- The access-code model for expense-recon and lead-desk, and who holds
  which code.
- Where the data lives and how to get a copy out.
- What the nightly and scheduled jobs are, and what breaks if they stop.

## 5. Consolidation, optional, after the transfer

The estate is four platforms wide for what is really two jobs. Once
ownership is clean, this reduces Brisken's operating surface:

- Merge the three static Vercel projects into one, using host rewrites as
  `brisken-onepilot` already does for `onepilot.brisken.com`.
- Co-host the expense-recon SPA bundle on the Fly app it already calls, so
  one deploy ships frontend and backend, and the Lovable publish step stops
  being a separate way for a change to sit unshipped.

Both are worth doing. Neither is worth blocking the transfer on.

## 6. On rebuilding in Lovable

Considered and not recommended as a handoff strategy. Lovable is a frontend
builder. It cannot host the FastAPI reconciliation engine, the SQLite
volumes, the Neon lead DB, or brisken.com, and rebuilding into it would
discard the Python engine (deterministic matcher, OCR, categorizer, Zoho
export) that is the actual product. It also does not remove a single account
dependency; it adds one. Keep Lovable where it already earns its place: the
expense-recon SPA, on a Brisken-owned seat.

## 7. Open items for Dirk

1. Who at Brisken holds the admin accounts, and who pays. Vercel team, Fly
   org, GitHub org, Lovable seat, Neon.
2. Whether Brisken wants lead capture to stay on Neon or move to whatever
   their team already runs.
3. Confirmation that Brisken IT will reissue the Graph client secret at
   cutover.
4. Whether any support arrangement continues after transfer, which decides
   whether we keep a member seat or are removed outright.
