# Phase 2, forwardable request to Brisken IT

Purpose: stand up a **read-only** integration that auto-logs Dirk's lead-gen
outreach (sent mail, replies, calendar meetings) into the internal Lead Desk so
pipeline status stops being maintained by hand. Nothing about this can send,
change, or delete anything; it reads Dirk's mailbox and calendar only.

Two parts below: a short note Dirk can forward as-is, then the exact steps for
IT and what to send back.

---

## Note to forward (Dirk -> IT)

Subject: Read-only app registration for the lead tracker (Dirk's mailbox only)

We are wiring my Rome/lead-gen follow-ups into an internal tracker so the
pipeline updates itself instead of me keeping a sheet current. It needs an
Entra app registration with read-only Graph access to my mailbox and calendar,
locked to my mailbox alone. It cannot send, edit, or delete, and it touches no
other mailbox. The worker runs in the EU (Frankfurt). Steps and the exact
permissions are below; when it is set up, please send back the Application
(client) ID and the client secret. Happy to jump on a quick call if that is
easier.

---

## Steps for IT

Tenant: `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74` (Brisken)
Target mailbox: `dirk.neumann@brisken.com` (the only mailbox this app may read)

**1. Register the application** (Entra ID -> App registrations -> New
registration).
- Name: `Brisken Lead Desk (read-only capture)`
- Supported account types: single tenant (this directory only)
- No redirect URI (daemon / app-only; there is no interactive sign-in)

**2. Grant application permissions** (API permissions -> Microsoft Graph ->
Application permissions, NOT delegated). Add exactly these two, then grant
admin consent:
- `Mail.Read`
- `Calendars.Read`

That is the whole list. No `Mail.Send`, no write scope, no `Mail.ReadWrite`,
no `User.Read.All`, no Files/Teams/SharePoint.

**3. Lock the app to Dirk's mailbox only** (Exchange Online PowerShell). By
default an application `Mail.Read` grant can read every mailbox in the tenant;
an Application Access Policy restricts it to one. This step is required, not
optional.

```powershell
# a mail-enabled security group whose only member is Dirk (or reuse an existing one)
New-DistributionGroup -Name "leaddesk-scope" -Type Security `
  -Members dirk.neumann@brisken.com -PrimarySmtpAddress leaddesk-scope@brisken.com

New-ApplicationAccessPolicy -AppId <APPLICATION_CLIENT_ID> `
  -PolicyScopeGroupId leaddesk-scope@brisken.com -AccessRight RestrictAccess `
  -Description "Lead Desk: restrict to Dirk's mailbox only"

# confirm: Dirk = Granted, any other mailbox = Denied
Test-ApplicationAccessPolicy -Identity dirk.neumann@brisken.com -AppId <APPLICATION_CLIENT_ID>
Test-ApplicationAccessPolicy -Identity <any-other-user>@brisken.com -AppId <APPLICATION_CLIENT_ID>
```

**4. Issue a credential** (Certificates & secrets). A client secret is fine; a
certificate is preferred if that is your standard. Note the expiry so it can be
rotated before it lapses.

**5. Send back** (the tenant ID we already have):
- Application (client) ID
- The client secret value (or the certificate)

Send the secret through your usual secure channel, not plain email. We store it
as an encrypted Fly.io secret; it is never committed to source control.

## What the integration does and does not do

- Does: every few minutes, reads new items in Dirk's SentItems / Inbox /
  Calendar, matches recipients to known lead contacts, and records the event
  (who, when, subject line) in the tracker. Idempotent by message id.
- Does not: send, reply, forward, flag, move, delete, or edit anything; read
  any other person's mailbox; read message bodies beyond what is needed to match
  a contact; write to the calendar; touch Teams, SharePoint, or Files.
- Hosting: EU (Frankfurt). Data stays in the EU. Only Dirk's own
  correspondence with the lead-gen contacts is recorded.

Least privilege in one line: two read scopes, one mailbox, one region,
rotatable credential, no write anywhere.

Credential decision (deferred to the 4d build): whether the capture worker
reuses the existing "BRISKEN MARKETING OPS INTEGRATION" app-only creds (already
Fly secrets, broader scope) or a dedicated least-privilege second app is
decided in the 4d Graph-sender build, not here. The capture code reads
`LEAD_DESK_TENANT_ID` / `LEAD_DESK_CLIENT_ID` / `LEAD_DESK_CLIENT_SECRET` and a
`LEAD_DESK_MAILBOXES` allowlist (dirk + matthias), so either choice is a
config-only change.
