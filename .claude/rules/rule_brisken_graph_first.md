# Brisken Graph-First Standard (M365 access)

**Hard constraint (owner directive 2026-07-14).** For Brisken Microsoft
365 work, every activity that falls within the Graph app's
implementation scope goes through **Microsoft Graph**, never through
desktop Outlook COM and never through CDP token-sniffing off the user's
Edge. "No more using desktop for Microsoft activities scoped within the
Graph implementation area." Desktop/CDP is a fallback ONLY for the
narrow set of M365 operations Graph is not yet provisioned to do, and
even then the correct move is to request the Graph grant, not to
default back to the desktop.

This rule is Brisken-scoped (mirrors [[rule_instantly_invasive]] as a
client-system rule). It supersedes, for Brisken mail/calendar READ, the
desktop-COM path in [[reference_dirk_outlook_com_drafts]] and the
token-sniffing path in [[reference_brisken_microsoft_planner]] /
[[reference_user_edge_cdp_9222]].

## The sanctioned mechanism

Graph app registration **"BRISKEN MARKETING OPS INTEGRATION"** (Entra,
tenant `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`), app-only
client-credentials. Secrets in the gitignored
`workspace/clients/brisken/context/.env`
(`BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`,
`BRISKEN_GRAPH_CLIENT_SECRET`). Never commit, never print the secret.
Mint: `POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`,
`grant_type=client_credentials`, `scope=https://graph.microsoft.com/.default`.
Granted roles (2026-07-14): `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`,
`Calendars.Read`, `Sites.Selected`, `Tasks.ReadWrite.All`. Full detail:
[[reference_brisken_graph_app_creds]].

## In scope → Graph only

| Activity | Graph path | Was (now banned for Brisken) |
|---|---|---|
| Read mail (inbox / sent / any folder) | app-only `GET /users/{mbx}/mailFolders/{f}/messages` (`$filter`, not `$search`) | desktop Outlook COM; CDP-sniffed token |
| Detect replies / bounces / reach-out | same, over both mailboxes | `brisken-mailbox-watch.py` COM reader |
| Create a draft / send mail | app-only `Mail.ReadWrite` / `Mail.Send` on the allowlisted mailbox | `Items.Add` COM draft-loader |
| Read calendar | app-only `Calendars.Read` | COM calendar scan |
| Planner / Tasks | `Tasks.ReadWrite.All` (app) or delegated token | CDP token off the planner tab |
| SharePoint files (the Rome master, decks) | Graph **workbook / drive API** (delegated `Files.ReadWrite.All` token, because the app's `Sites.Selected` is not granted for the MARKETING site) | raw-CDP SP REST from an Edge tab |

For the master sheet specifically: read/write via the Graph workbook
range API (surgical per-cell PATCH, coexists with the file open in
Excel Online, no full-file lock). Date columns are stored as ISO text,
so set `numberFormat` `[["@"]]` before writing a date string. Verify
any write by diffing the whole sheet vs a pre-edit snapshot.

## HARD mailbox allowlist (non-negotiable)

The credential is not yet restricted by an Exchange Application Access
Policy, so at the Microsoft layer it can act as ANY mailbox. Every
`Mail.*` / `Calendars.*` call MUST hard-allowlist the mailbox to
EXACTLY `dirk.neumann@brisken.com` and `matthias.silva@brisken.com`,
asserted in code before the call. No other mailbox, ever, regardless of
input. This is a compensating control until the Access Policy exists;
get that policy done when convenient, do not treat it as optional.

## Invasive-action gate still applies

Graph does not relax the invasive-action gate. Creating drafts,
sending mail, writing SharePoint/Planner, or any state-changing Graph
call in Brisken's live tenant is invasive: it needs an explicit
per-action owner yes and the plain-language scope-of-effects +
readiness check from [[rule_instantly_invasive]] /
[[feedback_no_invasive_action_without_ask]]. Read-only Graph
(mail/calendar/file/task reads) runs under autonomy. When sending as
Dirk via Graph, carry over the house conventions from
[[reference_dirk_outlook_com_drafts]] (recipient resolution, BCC the
Zoho dropbox `s9hitl_pv69mu@mails4.zohocrm.com` on customer mail) and
validate the first Graph-created draft before any batch.

## Out of scope (desktop/CDP fallback allowed, but prefer a grant)

Only where Graph genuinely cannot do it with current grants:
- **Calendar writes** (creating/updating events/invites): only
  `Calendars.Read` is granted. Request `Calendars.ReadWrite` rather
  than reverting to COM; until granted, a documented COM fallback is
  acceptable for a specific approved invite.
- **SharePoint sites not granted to the app** (`Sites.Selected`
  covers only granted sites): use the delegated `Files.ReadWrite.All`
  Graph token (still Graph, not CDP). Raw-CDP SP REST is a last
  resort only if no Graph token is available.
- Driving an authenticated *web UI* that has no API (rare): CDP Edge
  remains valid ([[reference_user_edge_cdp_9222]]) for genuine
  UI-only tasks, not for anything with a Graph endpoint.

Any desktop/CDP fallback must be announced with the reason it was
unavoidable ("LIMITATION: Graph lacks {grant}; used {fallback}").

## Enforcement

Honored at decision time. Before reaching for `win32com`, an Outlook
COM script, `brisken-mailbox-watch.py`, or a CDP `graph_token` sniff
on any Brisken M365 task, check whether the Graph app covers it; if it
does, using the desktop/CDP path instead is a friction event
(`brisken-graph-bypass`). Log at `/comd_checkpoint`. The recurrence-kill
is to widen the Graph grants (and this rule's table), not to keep the
desktop path warm.

## Why

Until 2026-07-14, Brisken M365 automation ran on two brittle,
machine-bound paths: desktop Outlook COM (requires Outlook running,
reads only what the profile has loaded, mis-files drafts across stores)
and CDP token-sniffing off the user's live Edge (hangs on busy
profiles, tokens expire in ~1h, disrupts the user's open tabs, and the
tenant's Exchange OData UserAgent allowlist (`ESAPRC_3`) 403s delegated
mail reads outright). The app registration removes all of that: a
clean, headless, tenant-sanctioned path that reads both mailboxes and
SharePoint without a browser or a running Outlook. The owner's
directive makes Graph the default and retires the desktop path for
everything Graph can now do.

Related: [[reference_brisken_graph_app_creds]],
[[reference_dirk_outlook_com_drafts]], [[reference_brisken_microsoft_planner]],
[[reference_user_edge_cdp_9222]], [[rule_instantly_invasive]],
[[feedback_no_invasive_action_without_ask]].
