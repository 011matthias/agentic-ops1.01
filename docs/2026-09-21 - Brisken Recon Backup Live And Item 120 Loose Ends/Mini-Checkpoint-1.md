# Mini-Checkpoint: Brisken Recon Backup Live And Item 120 Loose Ends

**Date:** 2026-09-21
**Status:** Item 120's docs half and all three loose ends closed; the backup is live and holding two copies
**Type:** mini

---

## Summary

Second checkpoint of this session. The first covered shipping item 120's
documentation-and-observability half; this one covers the tail, where the
SharePoint backup went from "one secret away" to actually running. Sibling
sessions closed the three loose ends and recorded them in PR #1175, so this
entry deliberately does not restate that: what it adds is the one finding
nothing else has written down, that the Graph credential cannot create a
SharePoint site.

## What Was Done

- **Established the backup was three settings, not one** (PR #1171, merged).
  `/data` measured 144.0 MB against the backup's 100 MB default ceiling, so
  `EXPENSE_RECON_BACKUP=1` alone would have refused on every round while
  reading as enabled. `EXPENSE_RECON_BACKUP_SITE` was unset as a second,
  separate refusal. The tool's own `backup --dry-run` on the live machine
  confirmed the measurement byte for byte. Corrected the "one secret" claim
  in backlog item 120, `docs/if-it-is-down.md`, and `backup.py`'s own size
  comment, which read `~95 MB (2026-09-17)` and was 49 MB stale four days on.
- **Proved the site-creation limit** (not recorded anywhere else). See
  Working Notes below.
- **Scoped the restart** for the owner: measured ~10 s end to end from the
  machine's event log, and confirmed against live state that nothing was
  owed, so a restart would resume no work and cost nothing.
- **Verified the backup after the fact.** Two archives in
  `MARKETING/ExpenseTool`, 127.2 MB each, 12 minutes apart (each boot fires
  one immediately, so a two-phase setup yields two). Neither carries a
  retention label.
- Appended the working raw-CDP browser path to
  `feedback_agent_browser_named_sessions` after its documented remedy failed.

## What Did NOT Work (and why)

- **Creating a dedicated SharePoint site:** the app cannot. Graph v1.0 has no
  site-creation endpoint, and the SharePoint-resource token mints but carries
  zero roles, so `_api/SPSiteManager/create` is unreachable. Read-only probes
  of `/_api/web` returned 401 on both the root and the MARKETING site.
- **Offering to verify after a permission grant** ("if you want the
  permission, add it and I'll verify"): blocked by `stop-b1-gate` as a
  deferral, correctly. The read-only half (probing whether SharePoint REST
  was reachable at all) was mine to take first, and taking it changed the
  answer: the Graph permission the portal most obviously offers would not
  have helped.
- **Asking which backup target to use:** the question was already moot. A
  sibling had set it up on MARKETING while the decision was being posed, and
  the user rejected the prompt. Should have re-read live state before asking.

## Current Status

Backup LIVE: daily to `brisken.sharepoint.com:/sites/MARKETING`, folder
`ExpenseTool`, all four secrets deployed. Two archives, 254.5 MB total, no
retention label on either. Fly v195 carries `640be61b`.

brisken platform: unknown plan, ops/mo not assessed; no assessment date in
`infrastructure.yaml`.

`p2-product-decks.md` (60d) and `p2-targeting.md` (61d) are stale and belong
to p2; deliberately untouched rather than bumped without the work.

## Next Steps

1. Set a retention rule on `MARKETING/ExpenseTool`, or move the schedule to
   weekly. 127.2 MB a day with nothing pruning is the only thing that grows.
2. Rehearse a restore. The copy is verified to exist and not verified to
   work; `docs/backup-and-restore.md` carries the procedure and says so.
3. Deploy PR #1170 so live `client_errors` rows gain `server_commit` /
   `server_image`; merged but not yet deployed, so the column starts at the
   next deploy.
4. Run `/ops-audit brisken` or record a platform assessment.
5. Log the Brisken comms conversations of the last 13 days.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 120)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/backup-and-restore.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md`

## Working Notes

**The Graph app cannot create a SharePoint site, and no Graph permission
fixes it.** Measured 2026-09-21, and worth keeping because the obvious next
move is wrong:

- Graph token roles: `Calendars.Read`, `Mail.Read`, `Mail.ReadWrite`,
  `Mail.Send`, `Sites.ReadWrite.All`, `Sites.Selected`, `Tasks.ReadWrite.All`.
  No `Sites.FullControl.All`, no `Sites.Manage.All`.
- Site creation is not a Graph v1.0 operation at all. It runs through
  SharePoint's `_api/SPSiteManager/create`.
- A token for `https://brisken.sharepoint.com/.default` MINTS but carries
  **no roles**, and `GET /_api/web?$select=Title` answers **401** on both the
  root and MARKETING.

So adding `Sites.FullControl.All` under **Microsoft Graph** would change
nothing; it would need the separate **Office 365 SharePoint Online** API
entry plus admin consent. The cheap path is a human creating the site and
handing over the URL, since `EXPENSE_RECON_BACKUP_SITE` is then one env var.
Recommended against the grant either way: permanent tenant-wide full control
over every SharePoint site, for a job that copies a zip.

Other live readings, 2026-09-21: `/data` 144.0 MB over 586 files (`runs`
83.3 MB, `inbound` 58.0 MB, root 2.7 MB); `/tmp` is the 8 GB root
filesystem, not the `/data` volume, so staging a 144 MB zip cannot trip the
intake's 200 MB disk floor; restart measured 6.8 s launch-to-started plus
~3 s to first `/healthz`.
