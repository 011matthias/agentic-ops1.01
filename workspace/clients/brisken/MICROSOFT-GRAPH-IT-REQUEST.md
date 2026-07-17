# Microsoft Graph access, consolidated IT request

Purpose: replace three separate, ad-hoc access methods (a manually
re-sniffed Planner bearer token, Outlook COM automation tied to a logged-in
Windows session, and a raw CDP session against SharePoint) with one Entra
app registration that covers mail, calendar, SharePoint, and Planner. This
is a bigger ask than the original mailbox-read-only request: it includes
send and write scopes. What each scope can and cannot do is spelled out
below so nothing is granted on an unclear premise.

Two parts: a short note Dirk can forward as-is, then the exact steps for IT
and what to send back.

---

## Note to forward (Dirk -> IT)

Subject: App registration for the lead tracker and marketing ops tooling

We are consolidating a few pieces of marketing/lead-gen tooling (the lead
tracker, the Rome contact sheet, Planner) onto one proper integration
instead of the workarounds we have been using. It needs an Entra app
registration with Graph access to my mailbox and Matthias Silva's mailbox,
the MARKETING SharePoint site, and Planner. Scopes and exact steps are
below. When it is set up, please send back the Application (client) ID and
the client secret. Happy to jump on a call if that is easier.

---

## Steps for IT

Tenant: `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74` (Brisken)
Target mailboxes: `dirk.neumann@brisken.com`, `matthias.silva@brisken.com`
(no other mailbox)

**1. Register the application** (Entra ID -> App registrations -> New
registration).
- Name: `Brisken Marketing Ops Integration`
- Supported account types: single tenant (this directory only)
- No redirect URI (daemon / app-only; there is no interactive sign-in)

**2. Grant application permissions** (API permissions -> Microsoft Graph ->
Application permissions, NOT delegated). Add exactly these six, then grant
admin consent:
- `Mail.Read`
- `Mail.ReadWrite`
- `Mail.Send`
- `Calendars.Read`
- `Sites.Selected`
- `Tasks.ReadWrite.All`

**3. Lock Mail and Calendar to the two mailboxes** (Exchange Online
PowerShell). By default `Mail.*` and `Calendars.*` application grants can
read and send as every mailbox in the tenant; an Application Access Policy
restricts that to a named group. Required, not optional.

```powershell
New-DistributionGroup -Name "marketing-ops-graph-scope" -Type Security `
  -Members dirk.neumann@brisken.com,matthias.silva@brisken.com `
  -PrimarySmtpAddress marketing-ops-graph-scope@brisken.com

New-ApplicationAccessPolicy -AppId <APPLICATION_CLIENT_ID> `
  -PolicyScopeGroupId marketing-ops-graph-scope@brisken.com -AccessRight RestrictAccess `
  -Description "Marketing ops integration: restrict Mail/Calendar to these two mailboxes"

# confirm: both mailboxes = Granted, any other mailbox = Denied
Test-ApplicationAccessPolicy -Identity dirk.neumann@brisken.com -AppId <APPLICATION_CLIENT_ID>
Test-ApplicationAccessPolicy -Identity matthias.silva@brisken.com -AppId <APPLICATION_CLIENT_ID>
Test-ApplicationAccessPolicy -Identity <any-other-user>@brisken.com -AppId <APPLICATION_CLIENT_ID>
```

**4. Issue a credential** (Certificates & secrets). A client secret is fine;
a certificate is preferred if that is your standard. Note the expiry so it
can be rotated before it lapses.

**5. Send back** (tenant ID we already have):
- Application (client) ID
- The client secret value (or the certificate)

Send the secret through your usual secure channel, not plain email.

---

## What happens after the credential lands (no further IT step)

- **SharePoint**: `Sites.Selected` grants no site access by itself. Once we
  hold the app credential, we (or a site owner) call the Graph API once to
  grant this app read/write on the one site we need, `/sites/MARKETING`
  (holds the Rome contact sheet and the product-deck library). No other
  SharePoint site is touched.
- **Planner**: `Tasks.ReadWrite.All` is live immediately on admin consent.
  No further step.

## What each scope actually grants, stated plainly

- `Mail.Read` + `Mail.ReadWrite` + `Mail.Send`: the app can read, edit, and
  send mail as `dirk.neumann@brisken.com` and `matthias.silva@brisken.com`.
  Restricted to those two mailboxes by the Application Access Policy above;
  no other mailbox is reachable. This is materially more than a read-only
  grant: it can send email as those two people. It replaces the current
  Outlook COM automation, which requires a logged-in Windows session and a
  scheduled task.
- `Calendars.Read`: read-only, same two mailboxes, same policy.
- `Sites.Selected`: no access until explicitly granted per site (step
  above); scoped to `/sites/MARKETING` only, not the rest of SharePoint.
- `Tasks.ReadWrite.All`: **this one has no scoping mechanism.** Microsoft
  Graph does not support restricting Planner application permissions to a
  single plan or group. Granting it means this app can read and write
  every Planner plan in Brisken's tenant, not just the MARKETING PLAN
  Lead Generation bucket we actually use. Flagging this so it is not
  discovered later; there is no narrower option available today.

## Status (2026-07-14)

App registered, all six application permissions consented and confirmed
live via a minted token, `Mail.Read` verified end-to-end against Dirk's
mailbox. The Application Access Policy in step 3 (locking Mail/Calendar to
the two mailboxes at the Exchange layer) has not been confirmed complete.
Until it is, this credential is capable of acting as any mailbox in the
tenant at the Microsoft layer; every caller of it enforces an
application-side hard allowlist to `dirk.neumann@brisken.com` and
`matthias.silva@brisken.com` as a compensating control (see
`context/graph-app-credentials.env`). That control does not protect
against the credential itself leaking; step 3 still closes that gap and
should be completed when convenient.

## Supersedes

This replaces `automations/lead-desk/PHASE2-IT-REQUEST.md`, which asked
only for read-only `Mail.Read` + `Calendars.Read` on Dirk's mailbox and was
never sent. That file should be deleted once this document is merged onto
a branch that has it (it currently exists on `main`, not on the branch this
document was written from).
