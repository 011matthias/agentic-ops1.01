# Brisken web estate: ownership, editing access, transfer runbook

Status: draft for owner review. Not sent to Dirk.
Prepared 2026-09-07; sections 4 to 11 rewritten 2026-09-10 as the access
model (fifteen agents: five live verifiers against the repo, Lovable, Fly,
GitHub/Cloudflare and Microsoft docs; three strategies; six adversarial
refutations; one synthesis; then the load-bearing facts re-probed by hand).
Every ownership fact names its evidence so it can be re-checked.

## 1. Why this exists

Every Brisken web property we built is currently hosted, billed and
administered under Matthias's personal accounts. That includes
**brisken.com itself**, Brisken's live corporate website. If those accounts
lapse, are suspended, or simply lose their operator, Brisken has no
administrative path back to their own site.

Owner direction 2026-09-09 added a second requirement: Dirk's team must be
able to **change** the assets themselves, front end and back end, without an
IDE and without Claude, and through as few applications as possible. So this
document answers two questions per asset: who owns it, and what a Brisken
person opens to change it.

## 2. What Brisken already owns (no action needed)

| Asset | Evidence |
|---|---|
| `brisken.com` domain + DNS | RDAP: registered at GoDaddy 2009-10-01, registrant BRISKEN, expiry 2028-09-30, auto-renew on, NS `pdns01/pdns02.domaincontrol.com`. **Correction 2026-09-10:** our GoDaddy API key (`context/registrar-api.env`, created 2026-07-09 inside the owning account) returns 200 and reads all 101 records; the 401 recorded on 2026-09-07 was a different, revoked key. The account is Brisken's, and it also holds non-Brisken domains, so it is somebody's personal GoDaddy login; whose is UNVERIFIED. Our key is zone-write power outside Brisken and is revoked at departure (section 6). |
| Entra app "BRISKEN MARKETING OPS INTEGRATION" | Tenant `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`. Brisken IT can revoke or reissue at will. An Exchange Application Access Policy is **live and enforcing** (proven 2026-09-10: `dirk.neumann@` and `matthias.silva@` open, `cristiane.cavalcanti@` refused with `Blocked by tenant configured AppOnly AccessPolicy`), scoped to the group "GraphOps Allowed Mailboxes". Runbook: gitignored `context/graph-access-policy-runbook.md`. |
| OpenAI API key running expense-recon | Dirk's own key (`OPENAI_API_KEY` on the Fly app). |
| Zoho CRM / Books | Brisken's tenant; we hold read-only OAuth credentials against it. |
| **A Lovable workspace** | Seven brisken.com hostnames resolve to Lovable's `185.158.133.1` and serve Brisken-built sites we never touched: `brisklet` (Brisklet Partner Program), `mbc-faq` (SAP MBC FAQs), `tac-2025`, `token`, `articles`, `insights`, `sap-ai-brief` (verified live 2026-09-10). Someone at Brisken already runs a Lovable workspace. Which account, which plan, and who administers it is UNVERIFIED and is the first question in section 9. |

Because Brisken controls DNS, no scenario locks them out permanently: worst
case they repoint `brisken.com` at new hosting and lose only the content,
which is in git. The transfer is about avoiding that fire drill, not about
preventing a hostage situation.

## 3. What we own that has to move or retire

### Vercel (account `matthias-5647` / neumath4@icloud.com, team `matthias-neumanns-projects`, id `team_MNNYUo2DofKqKUISX0X01rre`)

| Project | Project id | Domains served |
|---|---|---|
| `brisken-onepilot` | `prj_Avie4cXev9Axx4WfKNAJfob3FEap` | `brisken.com`, `www.brisken.com`, `onepilot.brisken.com` |
| `resources-site` | `prj_9EDCYbR0tJV7dwe8aC6HxbQYpuH9` | `resources.brisken.com` |
| `brisken-rome-hub` | `prj_EFYtjsRojr7xHONB9w4UhZg5JOAu` | `rome2026.brisken.com` |

The same team also holds `unpauseai-web`, `one-assessment-demo` and
`cv-generator`, which are ours and stay. `brisken-onepilot` additionally
carries a **Neon Postgres** database wired through the Vercel storage
integration (18 `DATABASE_*` env vars) behind `/api/book-demo`, plus
`NOTIFY_WEBHOOK_URL` pointing at an ntfy subscriber no document names. The
five legal PDFs (GTC, two privacy statements, MDH terms, the Accenture case
study) are served from **`brisken.com/docs/`** by this project, not from
`resources.brisken.com` (which returns 404 for `/docs/`), verified 2026-09-10.
`VERCEL_BRISKEN_TOKEN` in `context/.env` still answers 200 on 2026-09-10 and
is revoked at departure.

Under section 4 none of these projects transfer. They are retired after the
Lovable rebuilds go live.

### Fly.io (org `personal`, "Matthias Neum", account matneumann07@gmail.com)

| App | State | Persistent data |
|---|---|---|
| `brisken-expense-recon` | deployed, scale-to-zero | volume `recon_data` 1GB fra: SQLite ledger, receipts, cross-run memory. Criss's financial records. Owns the dedicated IPv4 `149.248.221.114` behind the `expenses.brisken.com` MX. |
| `brisken-lead-desk` | deployed | volume `lead_desk_data` 1GB fra: contacts + outreach events. Lead PII. |
| `brisken-onepilot` | suspended since June | volume `onepilot_data`; its review feedback was rescued 2026-09-09 |
| `brisken-onepilot-proto` | suspended since July | volume `onepilot_data`; same rescue |

Zero org or app tokens exist (`flyctl tokens list`, 2026-09-10), so the only
Fly credential is Matthias's login.

### GitHub (`011matthias`, no orgs)

| Repo | Role |
|---|---|
| `011matthias/brisken-expense-review` (private) | The expense-recon React SPA. Two-way synced with Lovable. |
| `011matthias/agentic-ops1.01` | Our monorepo. Brisken code lives under `workspace/clients/brisken/`; this repo does **not** transfer. |

### Lovable

Project `brisken-reconcile-dash.lovable.app` on Matthias's seat, connected to
`brisken-expense-review`, already published at `expenses.brisken.com` (the
lovable.app URL 302s there). Publishing is scriptable through the official
Lovable MCP server's `deploy_project`, and the dashboard Publish button is the
path a Brisken editor uses.

## 4. The access model in one paragraph

For Matthias: ownership moves before anything new gets built. The two Fly
apps go into a Brisken-owned Fly organisation with `fly apps move`, rehearsed
first on the dead proto app carrying a throwaway dedicated IPv4, so the one
undocumented question (does `149.248.221.114` survive the move) is answered
before Criss's records are touched. Everything with a face (brisken.com,
onepilot, resources, the expense screen) lives in a Brisken-owned Lovable
workspace: the three marketing sites are rebuilt there, the expense screen is
moved there. Vercel, Neon, the laptop notify task and the two review apps are
retired, not transferred. DNS stays at GoDaddy with no Cloudflare. Every
vendor account hangs off one shared mailbox, `platform@brisken.com`, with its
passwords in Brisken's vault, and both apps send as a second shared mailbox,
`tools@brisken.com`, with Dirk's own mailbox as the interim sender until IT
creates it. The Python backend stays configured, not edited, and this
document says so instead of promising otherwise.

For Dirk: your people open three things. Outlook, where sign-in links, receipt
acknowledgements and demo requests arrive. The tools in a browser: Criss at
expenses.brisken.com with her own code, you in the lead desk with a link
mailed to you, and one address with one sign-in for both once the
consolidation ships. Lovable, where your marketing editor changes brisken.com
by typing a request or clicking on the text, publishes as a separate step, and
can put back any earlier version. Brisken owns every account and every
invoice, holds every secret and a copy of Criss's ledger, and can restart,
re-key and back up the engine from a dashboard. Changing what the engine does
stays developer work, exactly as it is today.

## 5. Per-asset access table

| Asset | What a Brisken person edits it in | Who holds admin (Brisken identity) | What happens to it | Order | What breaks if wrong |
|---|---|---|---|---|---|
| brisken.com + www | Lovable project "brisken.com": inline text edits (free up to 100 per user per day), layout by prompt, drafts, Publish as a separate step, version restore. The five legal PDFs sit in this project's `public/docs/` and are never moved or renamed. | Brisken Lovable workspace, primary owner platform@; Dirk admin; the marketing editor as external collaborator on this project only | REBUILD in Lovable (no repo import exists; sync is export-only). The 18 Wix-era paths become TanStack loader redirects with status 301, verified with `curl -I`; client-side redirect pages if the runtime ignores the status. DNS at GoDaddy: apex A `185.158.133.1` plus the `_lovable` TXT, www and onepilot per Lovable's instructions, no AAAA. | 11 | A prompt that drops `public/docs/` breaks the footer GTC and privacy links that GDPR Art. 13/14 require. An editor can disconnect the domain (editors can on all plans). Rollback: revert to the Published-badged version, or repoint DNS to Vercel while it still exists. |
| onepilot.brisken.com | Same project, same editor | Same | REBUILD as a hostname on the brisken.com project (subdomains connect individually; the per-project hostname cap is unpublished) | 11 | Same as above |
| resources.brisken.com | Lovable project "resources": a new deck PDF is a file dropped into `public/` under the same name (every current file is under 2.3 MB, inside Lovable's 10 MB limit); page text inline | Same workspace; project owner platform@ | REBUILD as a second Lovable project. Decks and the ten generated deck pages carried over verbatim at their current root paths. GoDaddy CNAME replaced by A plus TXT. | 12 | A renamed file 404s every link Brisken has ever sent. Regenerating a deck page needs the generator, which lives in the source archive: developer work. |
| rome2026.brisken.com | None: retired | GoDaddy (Brisken's account) | RETIRE: delete its A records, add a GoDaddy subdomain forward with 301 to `https://brisken.com` (GoDaddy writes the DNS itself; brisken.com already uses GoDaddy nameservers), delete the Vercel project | 3 | Forwarding the apex by mistake replaces brisken.com's own A record; the forward goes on the subdomain only. |
| `/demo` lead capture (Neon) | The form is edited in the brisken.com Lovable project. Submissions arrive as mail in the tools@ inbox, read in Outlook. | tools@ shared mailbox members | RETIRE Neon and its 18 `DATABASE_*` vars with the Vercel project, after one CSV export. The rebuilt form sends a notification through Lovable's built-in email (TanStack Start server code, no Cloud, no secret; `notify.brisken.com` delegated by NS records plus a TXT at GoDaddy). Filing submissions into the lead desk is later developer work plus a Dirk decision, because `/events` parks unknown senders in the unmatched queue and creates no contact by owner decision (2026-07-14). | 11, 13 | Deleting Neon before the export loses every demo request ever submitted. Today's only egress is an ntfy push to a subscriber no document names. |
| expense-recon engine + volume `recon_data` | Not edited. Configured: settings through `PUT /api/settings` (fx rates, card to entity, card to account, merchant registry, `intake.known_senders`, `intake.alert_recipients`, `intake.retention_years`; which of these the SPA exposes is UNVERIFIED, the API accepts them all); Fly dashboard: secrets, restart, logs, scale | Brisken Fly org, two Admins (platform@ and dirk.neumann@); the app keeps its name because Fly apps cannot be renamed and this one owns the mail IP | TRANSFER by `fly apps move`, after the proto rehearsal and the lead-desk move. sftp copy of `/data` handed to Brisken first; an operator-downloadable export built before departure. | 7 | Volume snapshots cannot be restored across orgs, so the sftp copy is the only rollback. `min_machines_running=1` before P4 stops the four boot sweeps, including the ten-year retention deletion, with no log line. A path-prefix mount kills the mail listener. Restore is a flyctl operation with no dashboard equivalent. |
| expense-recon SPA (Lovable) | Lovable project "expense-review": prompt, draft, Publish, version restore. Only whoever Dirk names edits it; Criss uses it. | Brisken Lovable workspace; project owner platform@ | MIGRATE by Move workspace, after rehearsing a move with a throwaway project carrying a throwaway subdomain. The GitHub link breaks by design; the old repo is archived and zipped into the source archive. Stays Lovable-hosted at expenses.brisken.com (supersedes TARGET-ARCHITECTURE 4.2's co-hosting: Lovable's Publish is the only ship path a Brisken editor has). | 10 | Whether the connected domain survives the move is undocumented. Fallback: the project's lovable.app URL, which the API's CORS already admits, while the domain is re-added and the `_lovable` TXT re-verified at GoDaddy. |
| expenses.brisken.com mail intake (port 25 / `149.248.221.114` / MX) | None; `known_senders` and `alert_recipients` are settings (engine row) | Brisken Fly org (IP allocation) and GoDaddy (MX plus the A record behind `mx.expenses.brisken.com`, TTL 1800 s) | Moves with the app: the in-process aiosmtpd listener, the cert and the IP allocation ride along. IP survival is UNVERIFIED, so the proto rehearsal carries a throwaway dedicated IPv4 first and the A-record edit is staged. | 5, 7 | If the IP changes and DNS is not updated, receipts are refused until it is; senders retry, so mail is delayed, not lost. |
| lead-desk + volume `lead_desk_data` | In-app: Dirk approves and removes users (he is a seeded admin already), works contacts, review items and the unmatched queue. Fly dashboard: `LEAD_DESK_ADMIN_EMAILS`, the Graph triple, INGEST and WORKER secrets. `kill_switch` lives in the app's own state store, not in Fly secrets. Screens and sending logic: developer. | Brisken Fly org; in-app admins Dirk plus the named owner | TRANSFER by `fly apps move` (first data-bearing move; no dedicated IP, so the IP question does not apply). Break-glass login built before it. Lead desk inside tools.brisken.com (P6) only if the campaign sender stays unarmed. | 6 | The magic link is the only login. Without the break-glass, a Graph outage, an expired client secret or a sender-mailbox change locks Dirk out with a code deploy as the only recovery. |
| brisken.com DNS | GoDaddy DNS records page | Dirk's GoDaddy login; whose personal login owns the account is UNVERIFIED | NO CHANGE of registrar or nameservers, no Cloudflare. Only the records for the cutovers, the notify NS delegation and the `_lovable` TXTs change. M365, Zoho and the expenses MX are never touched. | 0, 3, 11, 12 | Our API key keeps zone-write power outside Brisken until it is revoked. Revoke it and rotate the GoDaddy password at departure. |
| Source repos | Not edited; developer work | Brisken SharePoint (the archive) and, recommended, a free Brisken GitHub org holding the same repos with no deploy automation; the Lovable projects hold their own code and version history | MIGRATE as an archive: subtree split of expense-reconciliation and lead-desk as zip plus git bundle, the deck-page generator with its logo fixtures, the runbook, the CI workflow file as a recipe, a zip of `brisken-expense-review`. Refreshed after the last deploy. The monorepo never transfers. | 1, 16 | An archive not refreshed after the last deploy hands Brisken stale source. Nobody at Brisken pushes code, so a repo with an auto-deploy would be a one-click untested production deploy of Criss's app; the org gets no Actions. |
| Notification mail sender identity | None; after step 1 it is a Fly secret a Brisken admin sets | tools@brisken.com shared mailbox (Dirk and the named owner read its bounces); interim dirk.neumann@, already allowlisted in both apps | REBUILD: the sending mailbox is read from an environment variable in both apps. The lead desk gets a separate system-sender variable for magic links and notifications, so `SEND_FROM` (the campaign identity) and the polled mailboxes are untouched. tools@ added to both code allowlists, to `rule_brisken_graph_first`, and to the "GraphOps Allowed Mailboxes" group. | 1, 9 | Both apps swallow send failures: a disabled matthias.silva@ today stops receipt acks, held-mail alerts and every lead-desk login with no error. Flipping `SEND_FROM` instead would change the campaign identity and stop polling replies to every historical auto-send. |
| Secrets (by name) | Fly dashboard (a Brisken admin); every value also in Brisken's vault | Brisken Fly org; Entra for the Graph client secret (IT) | Move with the apps (verified). expense-recon: `EXPENSE_RECON_AUTH_SECRET` (rotated step 8), `EXPENSE_RECON_OPERATOR_CODE` (deleted step 8), `EXPENSE_RECON_OPERATOR_CODES`, `EXPENSE_RECON_RECEIPT_FIRST`, `EXPENSE_RECON_AUTO_MATERIALIZE`, `EXPENSE_RECON_INTAKE_SMTP`, `OPENAI_API_KEY`, `BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`, `BRISKEN_GRAPH_CLIENT_SECRET` (reissued step 9), plus the new sender variable. lead-desk: `LEAD_DESK_AUTH_SECRET` (rotated step 6), `LEAD_DESK_INGEST_SECRET`, `LEAD_DESK_WORKER_SECRET`, `LEAD_DESK_AUTH_EMAILS`, `LEAD_DESK_BASE_URL`, `LEAD_DESK_ADMIN_EMAILS`, the same three `BRISKEN_*` values, plus the new system-sender variable. Retired: `BRISKEN_SITE_AUTH_SECRET` (with the proto app), `NOTIFY_WEBHOOK_URL` and the 18 `DATABASE_*` (with Vercel), `EXPENSE_RECON_NOTIFY_USER` (read only by the laptop script), `VERCEL_BRISKEN_TOKEN` (revoked; answers 200 today), the GoDaddy key in `context/registrar-api.env` (revoked). | 6 to 9, 17 | The Graph client secret has an expiry date nobody has recorded; on that date both apps stop sending with no log line and the lead desk locks out. Rotating an auth secret in the last five days of a month logs Criss out mid-close. |

## 6. The identity model

Two shared mailboxes carry the ownership, and they have different jobs.

**platform@brisken.com is the account email at every vendor.** A shared
mailbox needs no licence up to 50 GB, and Microsoft's own instruction is to
block its sign-in and keep it blocked, because every shared mailbox has an
Entra user with a system-generated password nobody is meant to use. So
platform@ can never do "Sign in with Microsoft" anywhere; it is the address a
vendor writes to. The vendor login is email plus password plus the vendor's
own TOTP, and both the password and the TOTP seed live in Brisken's vault,
readable by Dirk and the named owner. Verification codes, password resets and
billing mail land in an inbox both of them open from their own Outlook with
Full Access. This is Microsoft's emergency-access pattern applied to
third-party vendors: an account not associated with any individual,
credentials stored in a known secure location available to several
administrators, not on an employee's phone. Where a vendor refuses a role
address or offers no email login (UNVERIFIED for Lovable, whose login page is
script-rendered; Fly documents email sign-up), Dirk's own address becomes the
account email and platform@ the second admin.

**tools@brisken.com is what the tools send as.** Magic links, receipt
acknowledgements and held-mail alerts go out through the existing app
registration as app-only `POST /users/tools@brisken.com/sendMail`. Microsoft
documents that an application token with admin-consented Mail.Send can send
as any user in the organisation and that Graph mail covers shared mailboxes;
the specific combination has not been exercised on this tenant, which is why
the old sender stays alive until one real send is seen in tools@'s Sent Items.
Non-delivery reports land in the sender's Inbox, so bounced magic links are
visible to the two people who read tools@. Microsoft recommends a service
principal, not a user account, for a service hosted outside Azure, so the app
registration stays the identity for everything the Fly apps do against
Microsoft 365.

**Why two mailboxes.** The live Application Access Policy lets the app act
only on members of "GraphOps Allowed Mailboxes". tools@ joins that group
(shared mailboxes are scoped by group membership, which is exactly this
mechanism); platform@ stays out of it, so the app can never read the inbox
that receives vendor password resets. Microsoft has since replaced
Application Access Policies with RBAC for Applications and says not to create
new ones; the existing policy keeps working, and adding a member to its group
is not creating a policy. Migration to RBAC is a later IT task, not part of
this handover.

**Named people on top.** Dirk and the named owner each hold their own seat at
their own brisken.com address: Fly Admin (Fly's handover guide asks for two
admins), Lovable admin, Full Access on both mailboxes, and their own MFA on
their own authenticator. Criss holds a named recon code now and a magic link
after P3; she has no admin seat anywhere. The marketing editor is an external
collaborator on the two site projects, invited on their brisken.com address,
and sees no other project. No vendor here takes Entra sign-in on its plan (Fly
SSO is Google or GitHub only; Lovable SSO is Business and above), so the
tenant's MFA posture does not change.

**Matthias until departure, and how it ends.** Fly Member of the Brisken org
(the mover must be in both orgs), Lovable member for the move day and then an
external collaborator on named projects or nothing, deployer from his laptop
until the last deploy. His access dies in this order: removal from the Fly
org (no tokens exist to revoke); removal from Lovable; `VERCEL_BRISKEN_TOKEN`
revoked and the Vercel team left with nothing of Brisken's on it; the GoDaddy
API key revoked and the GoDaddy password rotated by Dirk; the Graph secret
reissued by IT so his copy stops working; his last deploy removes his address
from the lead desk's seeded admins (a code change plus a users-table row, not
an env edit); the final sftp copy of both volumes handed to Brisken before he
deletes his own copies and `context/.env`; his mailbox converted to a shared
mailbox rather than deleted, because the lead desk reads its Sent Items as
outreach truth and polls it for replies (that a conversion keeps the mail
without a licence is UNVERIFIED in this pass).

## 7. What Brisken logs into

Day-to-day, three:

1. Outlook, which exists today: the person's own mailbox for sign-in links
   and receipt acknowledgements, plus the tools@ inbox for bounces and demo
   requests (Dirk and the owner).
2. The tools in a browser: expenses.brisken.com (Criss, Dirk) and the lead
   desk (Dirk, at its fly.dev URL until P2 puts both behind tools.brisken.com
   with one sign-in).
3. Lovable: the Brisken workspace with the brisken.com, resources and
   expense-review projects (the marketing editor, Dirk, whoever edits the
   expense screen). Brisken's people already open this one for the seven
   microsites.

Admin-only, rare:

1. Fly dashboard (new): secrets, restart, logs, scale, billing, team.
2. GoDaddy (exists): DNS records for the cutovers, later renewals only.
3. Microsoft 365 admin center and Exchange PowerShell (exists, IT): shared
   mailboxes and members, the Graph secret, the allowed-mailboxes group.
4. Brisken's password vault (new if none exists): platform@ passwords and
   TOTP seeds, every secret value.
5. OpenAI platform and Zoho admin (exist, unchanged).
6. Google Search Console (optional, new): read-only, one more login under
   platform@.

Three day-to-day surfaces, none of them new to Brisken; five admin consoles,
of which Fly and the vault are new, plus one optional. Never opened by
Brisken: Vercel, Neon, Cloudflare, GitHub, Wix. Until a named owner exists,
Dirk is the operator of the admin consoles; the design does not pretend
otherwise.

## 8. What is editable and what is only configurable

**Marketing sites (brisken.com, onepilot, resources): editable, in Lovable.**
Text by clicking on it (free up to 100 edits per user per day), layout and new
sections by prompt (credits), files by upload into `public/` under 10 MB.
Every change is a version; the live site is a snapshot and moves only when
someone clicks Publish; rollback is reverting to the Published-badged version
and publishing again; drafts hold a change until it is accepted; Dirk reviews
on a shared preview link without an editor seat. No role limits an editor to
text: on every plan an editor can also disconnect the domain, manage project
access and publish. The guards are procedure: bookmark the sign-off version,
keep the five legal PDFs in `public/docs/` with a do-not-move note in the
project, and a runbook line that says "if brisken.com is dark, check Project,
Settings, Domains first". Cloud is never enabled on these projects; if it ever
is, the region is Europe and cannot be changed afterwards.

**Expense screen: editable, in Lovable, same mechanics.** Whoever Dirk names
edits it; Criss uses it. A screen that needs new data needs the Python
endpoint first, which is developer work. The SPA talks to the API by Bearer
token in localStorage against `brisken-expense-recon.fly.dev`; nothing on the
Lovable side changes that until P3.

**Engine: configured, never edited by a Brisken person.** Configuration lives
in three places. Settings JSON on the `/data` volume, written through
`PUT /api/settings`: merchant registry, fx rates, card to entity, card to
account, `intake.known_senders` (empty on production today, so only
brisken.com senders get acknowledgements), `intake.alert_recipients`,
`intake.retention_years` (default 10; the sweep that enforces it runs only
because scale-to-zero restarts the process, until P4). Which of these the SPA
exposes as fields is UNVERIFIED; the API takes all of them. Fly secrets in the
dashboard: `OPENAI_API_KEY`, the Graph triple, the operator codes,
`EXPENSE_RECON_RECEIPT_FIRST`, `EXPENSE_RECON_AUTO_MATERIALIZE`,
`EXPENSE_RECON_INTAKE_SMTP`, the sender variable. Fly dashboard actions:
restart, logs, scale. Not configurable: the matcher, OCR, the categoriser, the
LLM prompts, the Zoho Books mapping, the SMTP listener. Result-ready mail to
Criss does not exist in the app at all; it existed only in the laptop script,
which never reached her; building it is P4.

**Lead desk: configured.** In the app: approve and remove users, contacts,
review items, the unmatched queue, and `kill_switch`, which is app state, not
a secret. Fly secrets: `LEAD_DESK_ADMIN_EMAILS`, the Graph triple, INGEST and
WORKER secrets, the system-sender variable. Not configurable: screens, sending
logic, the campaign identity, and the ingest rule that no contact is ever
auto-created.

**Mail intake: nothing to edit.** The listener is in-process; its only knobs
are the two settings above and the MX record at GoDaddy.

## 9. Sequence

Two rules set the order. Every mechanism is rehearsed on something worthless
before it touches anything Brisken needs: a throwaway Fly app for the org
move, a throwaway Lovable project for the workspace move, rome2026 for GoDaddy
edits and Vercel deletion. Criss's ledger moves last, in its own window, with
nothing else changed that day.

0. **Prerequisites (Dirk, IT).** Dirk names the owner; confirms Brisken has
   a password vault or buys one; logs into the GoDaddy account that owns
   brisken.com and says who else can; names the Lovable account behind the
   seven brisken.com microsites. IT creates `platform@brisken.com` and
   `tools@brisken.com` as shared mailboxes (no licence, sign-in blocked, Full
   Access for Dirk and the owner), adds tools@ to "GraphOps Allowed
   Mailboxes", and records the current Graph client secret's expiry date.
   Verification: both mailboxes visible in Dirk's Outlook;
   `Test-ApplicationAccessPolicy` on tools@ says Granted; Dirk reads the zone
   in GoDaddy; the expiry date is in the runbook.

1. **Code before any move (Matthias, deployed from his laptop into the
   personal org as today).** (a) Sender read from an environment variable in
   both apps; the lead desk gets a separate system-sender variable so
   `SEND_FROM` and the polled mailboxes stay as they are; tools@ and
   dirk.neumann@ in both allowlists and in `rule_brisken_graph_first`;
   `test_capture_p8.py` updated; interim value dirk.neumann@, which needs
   Dirk's yes because his mailbox then sends system mail. (b) Lead-desk
   break-glass: a login path that needs no Graph mail, armed by setting one
   Fly secret and consumed on first use. (c) Recon export: an
   operator-downloadable archive of the ledger and receipts, so a Brisken
   person can take a copy without a CLI. (d) `intake.alert_recipients` set to
   Criss and Dirk through settings. (e) `snapshot_retention` raised in
   `fly.toml` if Fly allows it (UNVERIFIED). (f) First source archive
   delivered to Brisken SharePoint. Verification: a magic link arrives from
   dirk.neumann@ and redeems; a receipt sent from a brisken.com mailbox comes
   back acknowledged from dirk.neumann@ (acks go only to known senders and
   that list is empty, so a cold outside mailbox proves nothing); both sends
   visible in that mailbox's Sent Items; the break-glass used once and
   re-armed; the export downloaded and opened.

2. **Disable BriskenReconNotify on the laptop.** No verification needed:
   Criss never received its mail and the app has no result-ready path, so
   nothing Brisken sees changes. It would die at step 8 anyway, since it logs
   in with the legacy shared code.

3. **rome2026.** Dirk or the owner deletes the A records in GoDaddy and adds
   a subdomain forward, 301 to `https://brisken.com`; Matthias deletes the
   Vercel project. Verification: `curl -I https://rome2026.brisken.com` shows
   301 to brisken.com. First Brisken-hand GoDaddy edit, and the rehearsal for
   deleting Vercel projects.

4. **Brisken Fly organisation.** The owner signs up with platform@ (email
   sign-up is documented), creates the org, adds Brisken's card, invites
   dirk.neumann@ as Admin and Matthias as Member. Verification: Dirk opens the
   dashboard and sees the org; the billing page shows the card.

5. **Rehearsal on brisken-onepilot-proto.** Allocate a $2 dedicated IPv4 to
   it, note the address, move it (`fly apps move` or the dashboard's Move app
   button), run `fly ips list`, and record whether its stopped Machine moved
   without intervention. Then destroy both review apps and release the
   throwaway IP. Verification: the ips output before and after, pasted into
   the runbook; if the address changed, the recon move gets a staged DNS
   edit.

6. **Lead-desk move.** sftp copy of `/data` to Brisken SharePoint;
   `fly apps move brisken-lead-desk`; verify `/healthz`, Dirk's magic-link
   login from a private window, contact count unchanged, `kill_switch` still
   1. In a later window a Brisken admin rotates `LEAD_DESK_AUTH_SECRET` from
   the dashboard (value into the vault) and Dirk logs in again; INGEST and
   WORKER are rotated once whatever still posts to `/events` is known
   (UNVERIFIED today).

7. **Recon move**, outside Criss's hours, never in the last five days of a
   month, nothing else changed the same day. Read the failing check's output
   and the last logs first (the Machine sat stopped with one warning on
   2026-09-10), start it, get the check green; sftp copy of `/data` to
   Brisken; stage the GoDaddy edit for the A record behind
   `mx.expenses.brisken.com`; move. Verification: `fly ips list` shows
   `149.248.221.114` (otherwise apply the DNS edit, TTL 1800 s); `/healthz`;
   a receipt from a brisken.com mailbox acknowledged; the SPA loads the
   ledger.

8. **Codes, a separate window.** `EXPENSE_RECON_OPERATOR_CODES` gets a code
   each for Criss and Dirk; `EXPENSE_RECON_OPERATOR_CODE` is deleted (the
   gate stays on while named codes exist); `EXPENSE_RECON_AUTH_SECRET` rotated
   once, which kills every token Matthias ever issued and logs everyone out
   once. Verification: Criss and Dirk each log in with their own code. Named
   codes give attribution, not revocation: removing a code stops new logins
   with it, and existing tokens stay valid until the secret is rotated again.

9. **Graph, when IT delivers.** New client secret set on both apps from the
   dashboard; a magic link and an ack verified; then IT deletes the old
   secret, which is where Matthias's copy dies. Sender switched from
   dirk.neumann@ to tools@ by changing the two Fly secrets, verified by a
   magic link arriving from tools@ and its copy in tools@'s Sent Items. IT
   puts the new secret's expiry in a calendar IT owns. Runbook line: "if
   magic links stop arriving, check the Graph secret expiry first".

10. **Lovable workspace and the expense screen.** Workspace: the existing
    Brisken one if Dirk names it and its members are acceptable editors of
    Criss's screen (on Pro every member sees and can edit every project),
    otherwise a new Pro workspace under platform@ with Dirk as admin;
    per-member build-credit caps and auto top-up on. Rehearsal: a throwaway
    project in Matthias's workspace with a throwaway subdomain
    (`test.brisken.com`, A `185.158.133.1` plus TXT) is moved and its Domains
    page read. Then the expense-review project is moved outside Criss's
    hours. Verification: Project, Settings, Domains reads Live; the screen
    loads at expenses.brisken.com from a private window; fallback is the
    project's lovable.app URL. Bookmark the current version as sign-off;
    transfer project ownership to platform@; archive
    `011matthias/brisken-expense-review` and add its zip to the source
    archive.

11. **brisken.com, www, onepilot.** New TanStack Start project; the four
    pages rebuilt by prompt from the live site; `public/docs/` carries the
    five legal PDFs verbatim (`brisken-cloud-services-gtc.pdf`,
    `brisken-privacy-statement-2021.pdf`,
    `brisken-privacy-statement-2018.pdf`,
    `brisken-market-data-hub-terms.pdf`,
    `brisken-accenture-case-study.pdf`); the 18 Wix-era paths as loader
    redirects with status 301; the demo form sends a notification to tools@
    through Lovable's built-in email (a workspace admin adds
    `notify.brisken.com` by NS delegation plus TXT at GoDaddy). Pre-DNS
    verification on the lovable.app URL: every `/docs/*.pdf` returns 200;
    `curl -I` on each legacy path shows 301 (otherwise swap in client-side
    redirect pages); a form submission from a private window lands in tools@;
    Dirk signs off the preview link. DNS at GoDaddy: apex A `185.158.133.1`
    plus TXT `_lovable`, www and onepilot per Lovable's instructions, no AAAA.
    Post-DNS: the same checks from a private window, plus the marketing
    editor's first inline edit published.

12. **resources.brisken.com.** Second project; every PDF and the ten deck
    pages at their current root paths; a scripted list of every current
    resources URL checked for 200 on the lovable.app URL before the CNAME is
    replaced by A plus TXT, and again after.

13. **Vercel and Neon.** Seven days after each cutover, confirm the hostname
    resolves to `185.158.133.1`, export the book-demo table from the Neon
    console as CSV to Dirk, then delete the storage integration and the
    project; `brisken-onepilot` last. Revoke `VERCEL_BRISKEN_TOKEN`. The
    Hobby non-commercial exposure ends here.

14. **Search Console, optional.** Claim brisken.com by DNS TXT so the
    legacy-path question stops resting on an unmeasured number. One Google
    login under platform@.

15. **Consolidation, developer work on infrastructure Brisken already owns,
    only if time allows.** P2 (tools.brisken.com Host-header router, never a
    path prefix); P3 (recon becomes the magic-link issuer; the SPA is Bearer
    over localStorage against `brisken-expense-recon.fly.dev`, so P3 includes
    a Lovable-prompted SPA change, and the session cookie stays host-only
    because a `Domain=.brisken.com` cookie would travel to every
    Lovable-hosted and Zoho-hosted subdomain); P4 (scheduler, sweep
    conversion and `min_machines_running=1` shipped together); P6 only if
    the campaign sender stays unarmed. `PROJECT-BOUNDARIES.md` is amended
    first, as it demands. If none of this ships, Brisken has two addresses
    and named codes, and owns everything anyway.

16. **Source archive refreshed after the last deploy.** Zip and git bundle
    of both apps, the deck-page generator with its logo fixtures, the CI
    workflow as a recipe (the monorepo already runs the recon suite in CI),
    and the runbook: every secret by name and purpose; restart, rotate,
    export; restore via flyctl; why `min_machines_running` stays 0 until P4;
    that both `fly.toml` headers describe access codes that no longer exist;
    that `kill_switch` lives in the app. Push the same into the Brisken
    GitHub org if one was created.

17. **Proof, then removal.** A Brisken person, cold, with Matthias watching
    and not touching: an inline edit published to brisken.com; a Fly secret
    changed and the Machine restarted from the dashboard; a magic-link login;
    a receipt from a brisken.com mailbox acknowledged; the export downloaded;
    the break-glass exercised and re-armed. Then the removal list from
    section 6, in that order, with matthias.silva@ converted to shared rather
    than deleted.

## 10. Decisions only Dirk can make

1. **Who at Brisken owns this, by name?** The person who restarts the
   Machine at nine in the evening, holds the second Admin seat on Fly and
   Lovable, reads platform@ and tools@, and runs the restore, which is a
   flyctl operation with no dashboard button. Without a name nothing moves
   and the estate stays on a Gmail-registered Fly account and a personal
   Vercel team. If the name is an IT engineer, the Azure route
   (TARGET-ARCHITECTURE P7) reopens and a GitHub org gets created now; if
   not, the archive is the home of the source until a developer is engaged.

2. **Which Lovable workspace, and Pro or Business?** The account behind the
   seven microsites exists somewhere; reusing it means one subscription. On
   Pro ($25 per month, 100 credits) every member can edit and publish every
   project, including Criss's screen; the marketing editor as an external
   collaborator on the two site projects covers that, but only if the
   workspace's other members are acceptable editors of the expense screen.
   Otherwise the expense screen gets its own Pro workspace or the workspace
   goes to Business ($50 per month, restricted projects). An editor on any
   plan can disconnect the domain.

3. **Will IT do five things, and when?** Create platform@ and tools@; add
   tools@ to "GraphOps Allowed Mailboxes"; reissue the Graph client secret at
   cutover and own its expiry; convert matthias.silva@ to shared at departure
   instead of deleting it. IT has delivered before (the Access Policy is
   live), so the ask is small. Interim if the mailboxes are slow: Dirk's own
   mailbox sends the magic links and acknowledgements and receives the
   bounces, which needs his yes; otherwise the estate keeps depending on
   Matthias's mailbox.

4. **Shared code, named codes, or per-person sign-in for the expense tool?**
   Named codes cost nothing and give attribution; revoking anyone still means
   rotating the secret and everyone logging in again. Per-person sign-in (P3)
   is about 1.5 developer-weeks (estimate UNVERIFIED) that must land before
   departure, never in the last five days of a month. Dirk chose sharing in
   August; that choice now has a cost he had not seen.

5. **Where do demo requests go?** Into the tools@ inbox as mail, now, with
   zero new systems; or into the lead desk later, which needs a developer to
   build an intake endpoint and Dirk to reverse the 2026-07-14 rule that no
   contact is ever auto-created. Today they go into a table nobody reads and
   a push notification nobody at Brisken can name.

6. **The 18 Wix-era redirects.** In-app 301s (unverified on Lovable's
   runtime) with Search Console claimed so the traffic becomes a number; or
   Cloudflare, which is one more admin console, a nameserver move for the
   whole zone including the Microsoft 365 mail records, and a proxy mode
   Lovable does not monitor. The traffic has never been measured.

7. **Does Brisken have a password vault?** If not, buy one before any vendor
   account is created; otherwise platform@'s TOTP seeds end up on one phone
   and die with it.

8. **Retention period for the financial records.** The engine deletes after
   ten years (AO §147); Dirk's guess was seven years US. It is a setting now
   (`intake.retention_years`), and the sweep that enforces it stops silently
   if the Machine is set always-on before P4.

9. **Is the old Wix account still taking form submissions, and who holds
   it?** The only two real inbound enquiries came through it. Open and
   unwatched, it swallows leads; closed without a forward, likewise.

## 11. Claims this plan rests on, and their status

| Claim | Status | Source |
|---|---|---|
| `fly apps move` carries Machines, Volumes with data, env vars, secrets, certificates and domain names; only Fly Postgres is excluded; the mover must be in both orgs | verified | fly.io/docs/apps/move-app-org/ ; app-handover-guide |
| The dedicated IPv4 `149.248.221.114` survives the move | UNVERIFIED (docs silent; a Fly staffer says IPs are not floating between apps, which is a different question) | community.fly.io/t/ipv4-move-between-apps/9811; gate is step 5 |
| A stopped Machine with an attached volume moves without intervention | UNVERIFIED | docs silent |
| Volume snapshots cannot be restored into another org | verified (open docs issue) | github.com/superfly/docs/issues/1981 |
| Automatic snapshots on `recon_data` are retained 5 days | verified | `flyctl volumes snapshots list` 2026-09-10 |
| `snapshot_retention` can be raised in `fly.toml` | UNVERIFIED | none |
| Fly dashboard can set secrets, restart, scale, tail logs, move an app, manage team and billing; it cannot edit code | verified | Fly community announcements 2024 to 2026 |
| Fly does not revoke a removed member's tokens; zero org and app tokens exist today | verified | fly.io/docs/security/remove-org-member/ ; `flyctl tokens list` 2026-09-10 |
| Fly account sign-up with an email address only; org SSO is Google or GitHub only | verified | fly.io/docs/getting-started/sign-up-sign-in/ ; fly.io/docs/security/sso/ |
| App-only Mail.Send sends as any mailbox; Graph mail covers shared mailboxes; a shared mailbox has a blocked-sign-in user object and needs no licence up to 50 GB | verified | learn.microsoft.com outlook-send-mail-from-other-user; outlook-mail-concept-overview; about-shared-mailboxes |
| That send works on the Brisken tenant for tools@ | UNVERIFIED (never exercised here) | step 9 verification |
| The Application Access Policy is live and scoped to "GraphOps Allowed Mailboxes"; shared mailboxes are scoped by adding them to that group | verified | differential probe 2026-09-10 (`context/graph-access-policy-runbook.md`); learn.microsoft.com new-applicationaccesspolicy |
| Application Access Policies are replaced by RBAC for Applications and new ones should not be created; existing ones keep working | verified | learn.microsoft.com new-applicationaccesspolicy; permissions-exo/application-rbac |
| The current Graph client secret's expiry date | UNVERIFIED (never recorded) | MICROSOFT-GRAPH-IT-REQUEST.md step 4 |
| Converting matthias.silva@ to a shared mailbox keeps its mail without a licence | UNVERIFIED; the lead desk's dependence on its Sent Items is verified | truth_scan.py; cloud_worker.py |
| Both apps hard-code matthias.silva@ as sender; dirk.neumann@ is already allowlisted in both; the lead desk's `SEND_FROM` is the campaign identity and polling set | verified | graph_notify.py; graph_mail.py; cloud_worker.py |
| Named operator codes give attribution only; tokens never expire and are not checked against the code list; rotating `EXPENSE_RECON_AUTH_SECRET` invalidates all tokens | verified | expense-recon web/auth.py |
| Receipt acknowledgements go only to brisken.com senders or `intake.known_senders`, which is empty on production | verified | intake_mail.py; status/p1 |
| `alert_recipients`, `known_senders` and `retention_years` are settings writable via `PUT /api/settings`; which of them the SPA exposes | verified; UNVERIFIED | intake_mail.py; app.py |
| The app has no result-ready mail path; `EXPENSE_RECON_NOTIFY_USER` is read only by the laptop script | verified | tools/brisken-recon-notify.py |
| The SPA hard-codes `API_BASE` = `brisken-expense-recon.fly.dev` and uses a Bearer token from localStorage, not a cookie; the API's CORS admits any lovable.app origin and `https://expenses.brisken.com` | verified | brisken-expense-review src/lib/api.ts; expense-recon web/app.py |
| `/events` never creates a contact; unknown senders go to the unmatched queue | verified | lead-desk web/service.py; app.py |
| `kill_switch` is app state, not a Fly secret; matthias.silva@ is in the seeded admins and the users table | verified | cloud_worker.py; lead-desk web/auth.py; store.py |
| What still posts to `/events` with `LEAD_DESK_INGEST_SECRET` | UNVERIFIED | none |
| Lovable secrets are a Cloud feature; a paused Cloud backend does not wake on traffic | verified | docs.lovable.dev/features/secrets ; advanced-settings |
| Lovable's built-in email works from TanStack Start server code without Cloud; paid plan; 50,000 per month; domain added by NS delegation plus TXT by a workspace admin | verified | docs.lovable.dev/features/custom-emails |
| GoDaddy accepts NS records on the notify subdomain | UNVERIFIED on this zone | none |
| Lovable serves `public/` files at root paths; Lovable cannot save files over 10 MB | verified (live probe on two Lovable-hosted brisken.com hosts; the 10 MB line in the docs) | expenses.brisken.com/favicon.png 200; docs.lovable.dev/features/projects/chat |
| A TanStack Start loader redirect with status 301 is honoured on Lovable hosting | UNVERIFIED | step 11 `curl -I` |
| The five legal PDFs are served from brisken.com/docs/, not resources.brisken.com | verified | curl 2026-09-10 (200 on brisken.com, 404 on resources) |
| Every PDF and deck page is under 2.3 MB | verified | file sizes in website/docs/ and resources-site/ |
| Moving a Lovable project breaks its GitHub link; the project keeps history and settings | verified | docs.lovable.dev/integrations/github FAQ |
| expenses.brisken.com is already connected and primary on the SPA project | verified | lovable.app 302 to expenses.brisken.com |
| A connected domain survives Move workspace; a moved project keeps its lovable.app URL; the mover must be a member of the destination workspace | UNVERIFIED | step 10 rehearsal |
| Lovable Pro $25 per month for 100 credits; Business $50; members free; per-member build-credit caps; custom domains need a paid plan | verified | docs.lovable.dev/introduction/subscription-plans; features/workspace |
| External collaborators limited to specific projects; on Pro every member can edit every project; editors can disconnect domains and publish on all plans | verified | docs.lovable.dev/features/share-project; collaboration |
| Lovable accepts platform@ as an account email with an email login | UNVERIFIED | fallback: Dirk's address |
| A Brisken-owned Lovable workspace already holds the seven microsites; its owner and plan | sites verified live; owner UNVERIFIED | nslookup + curl 2026-09-10 |
| GoDaddy subdomain forwarding: 301, HTTPS applied, DNS written by GoDaddy, requires GoDaddy nameservers | verified | godaddy.com/help/forward-my-godaddy-domain-12123 |
| GoDaddy: registrant BRISKEN, expires 2028-09-30, auto-renew on; our API key returns 200 today | verified | GoDaddy API 2026-09-10 |
| Cloudflare partial (CNAME) setup needs Business; on Free the nameservers move | verified | developers.cloudflare.com/dns/zone-setups/partial-setup/ |
| expenses MX points at `149.248.221.114` with TTL 1800 s; no AAAA on any Brisken host | verified | nslookup 2026-09-10 |
| `VERCEL_BRISKEN_TOKEN` is live | verified | api.vercel.com/v2/user 200, 2026-09-10 |
| Vercel Hobby forbids commercial custom domains | verified | vercel.com/docs/plans/hobby |
| `min_machines_running=1` before P4 stops the four boot sweeps silently; path-prefix mounting kills the SMTP listener | verified | TARGET-ARCHITECTURE.md sections 3 and 5 |
| Developer-week estimates for P2, P3, P4 | UNVERIFIED (inherited) | TARGET-ARCHITECTURE.md section 7 |
| Brisken has a password vault | UNVERIFIED | step 0 |
| The ntfy push subscriber behind `/api/book-demo` | UNVERIFIED (no document names it) | TARGET-ARCHITECTURE.md section 8 |
| Search Console for brisken.com is unclaimed | verified | TARGET-ARCHITECTURE.md 1b |
| The lead desk has no break-glass login today | verified | memory project_brisken_lead_desk |
| `PROJECT-BOUNDARIES.md` forbids p1/p2 shared infrastructure and must be amended before P2 | verified | PROJECT-BOUNDARIES.md |

## 12. What was considered and not taken

- **Cloudflare in front of Lovable holding the redirect table** (decided in
  TARGET-ARCHITECTURE 1b on 2026-09-09, superseded here). Partial setup needs
  Business, so the whole zone's nameservers would move, putting Dirk's and
  Criss's Microsoft 365 mail records in a 24-hour blast radius for 18
  redirects nobody has measured; it adds an admin console; rome2026 needs one
  GoDaddy forward instead. Revisit only if Search Console shows real
  legacy-path traffic.
- **Transferring the Vercel projects to a Brisken team.** Vercel requires the
  transferring user to be a member of the paid target team, for sites that
  are leaving Vercel anyway; a frozen Vercel project serves the same fallback
  at no cost until the Lovable cutover.
- **A GitHub Action deploying the Fly apps on push.** An auto-deploy on push
  is a one-click untested production deploy of Criss's app by people who do
  not push code. The org, if created, holds source only.
- **The demo form posting into the lead desk's `/events` via a Lovable
  secret.** Lovable secrets require Cloud, which auto-pauses and does not
  wake on traffic; `/events` parks unknown senders and notifies nobody.
  Lovable's built-in email to tools@ needs none of that. A Lovable Cloud
  table for the form fails the same way: a paused backend drops submissions
  silently.
- **Named operator codes as per-person revocation.** The token is
  HMAC(secret, role:label) with no expiry and no check against the code list;
  revocation is a secret rotation that logs everyone out. Kept as attribution
  only.
- **The `Domain=.brisken.com` cookie as the "small P3 task"**
  (TARGET-ARCHITECTURE 4.4). The SPA uses Bearer over localStorage and no
  cookie at all; a parent-domain cookie would travel to Lovable-hosted and
  Zoho-hosted subdomains. P3's design is reopened, not assumed.
- **Flipping `SEND_FROM` in the lead desk to the new sender.** `SEND_FROM` is
  the campaign identity and half the polled mailbox set; a separate
  system-sender variable is the right shape.
- **Disabling matthias.silva@ as the last offboarding step.** The lead desk
  reads that mailbox's Sent Items as outreach truth and polls it for replies;
  convert to shared instead.
- **Bundling the recon move with the code re-issue, the auth-secret rotation
  and the Graph secret reissue in one window.** Five independent failure
  sources on the one asset that holds Criss's records; split into steps 7, 8
  and 9.
- **Transferring primary ownership of Matthias's Lovable workspace.** The
  previous owner stays an owner, and the workspace holds non-Brisken
  projects. Move the project, not the workspace.
- **The SPA co-hosted in the Fly container, built in CI**
  (TARGET-ARCHITECTURE 4.2, superseded here). Lovable's Publish is the only
  ship path a Brisken editor has; co-hosting removes it and reintroduces a
  deploy nobody at Brisken can run.
- **Migrating the Application Access Policy to RBAC for Applications now.**
  The live policy keeps working; adding tools@ to its group is one cmdlet.
  Migration is IT housekeeping for later, not a handover dependency.
- **Azure with Entra sign-in as plan of record.** Stays conditional on IT
  naming an owner, as TARGET-ARCHITECTURE already decided; Azure Container
  Apps is dead on the port-25 constraint.
