# Backup and restore (backlog item 119)

**No restore has been rehearsed.** Everything below is written from the
code and from Fly's documented behaviour, and the one step that would
prove it (restoring into a throwaway app) needs the owner's go-ahead
because it costs a second machine and a second volume. Treat the restore
half as untested until that run happens, and do it before anyone has to
rely on it in anger.

**If the app is DOWN rather than lost, start at
[`if-it-is-down.md`](if-it-is-down.md)** (item 120): which of the three
services is down, the three failure shapes, and the deploy and rollback
paths. Come back here only when the data itself has to be recovered.

## What exists today

| Copy | Where | Who controls it | Age |
|---|---|---|---|
| The live data folder | `/data` on the `recon_data_v2` volume, Frankfurt | the developer's personal Fly account | current |
| Platform snapshots | Fly, same account | the developer's personal Fly account | 5 days, 5 snapshots |
| The SharePoint copy | the site in `EXPENSE_RECON_BACKUP_SITE`, folder `EXPENSE_RECON_BACKUP_FOLDER` | Brisken | as often as the schedule runs |

The third row is what this round added, and it is the only copy Brisken
itself holds. It is **off until someone turns it on**: with
`EXPENSE_RECON_BACKUP` unset the app starts no backup thread.

## Taking a copy

```bash
# say what would be uploaded, read nothing but the volume (the default)
expense-recon backup --data /data

# resolve the target and list what is already there; read-only Graph
expense-recon backup --check

# take one copy now
expense-recon backup --data /data --go
```

Settings, all environment variables:

| Variable | Meaning |
|---|---|
| `EXPENSE_RECON_BACKUP_SITE` | the SharePoint site, as Graph addresses it: `brisken.sharepoint.com:/sites/MARKETING` |
| `EXPENSE_RECON_BACKUP_FOLDER` | folder inside the site's default document library (default `Expense Reconciliation Backups`); created on the first upload |
| `EXPENSE_RECON_BACKUP` | `1` turns the in-app schedule on. Unset = off |
| `EXPENSE_RECON_BACKUP_INTERVAL_HOURS` | how often the schedule runs (default 24) |
| `EXPENSE_RECON_BACKUP_MAX_BYTES` | refuse above this size (default 100 MB; the folder is about 95 MB) |

The credential is the app-only Graph registration the estate already holds
(`BRISKEN_TENANT_ID`, `BRISKEN_GRAPH_CLIENT_ID`,
`BRISKEN_GRAPH_CLIENT_SECRET`, already Fly secrets for the mail notifier).
No mailbox is involved: this is the drive API.

The copy is one zip per run, named
`expense-recon-data-YYYYMMDDTHHMMSSZ.zip`, holding the data folder with
its paths intact. Live databases are copied through SQLite's own backup
API rather than off the disk, so a copy taken mid-write restores as a
readable database rather than as "database disk image is malformed".

## Restoring

1. **Fetch the newest copy.** Open the backup folder in SharePoint and
   take the zip with the newest name (the name IS the UTC timestamp, so
   newest name is newest copy; do not trust the modified column, which a
   re-upload changes). Or read the folder with
   `expense-recon backup --check`, which prints the names and sizes.
2. **Decide what you are restoring into.** A rehearsal goes into a
   throwaway app with its own volume, never the live one. A real recovery
   goes into the live app, and the live `/data` should be copied aside
   first if the machine still runs at all: a bad restore over a working
   folder is worse than the problem it is fixing.
3. **Stop the app** so nothing writes while files are replaced:
   `flyctl scale count 0 -a <app>`. The mailbox goes down with it, and
   senders' mail systems retry, so a restore window of minutes costs
   nothing permanent.
4. **Put the files back.** Upload the zip to the machine and unpack it
   over `/data`:
   ```bash
   flyctl scale count 1 -a <app>            # a machine to copy into
   flyctl ssh sftp shell -a <app>           # put the zip in /data/restore.zip
   flyctl ssh console -a <app> -C "sh -c 'cd /data && unzip -o restore.zip && rm restore.zip'"
   ```
   Unpacking over the folder replaces what the copy holds and leaves
   anything newer in place; for a clean restore, move `/data` aside first
   and unpack into an empty folder.
5. **Restart and check.** `flyctl apps restart <app>`, then:
   - `GET /healthz` answers `status: ok`, and its `disk` block shows the
     volume with free space above the floor;
   - the months list shows the months the copy held, with the same
     counts. Open one and check a receipt renders, which proves the run
     database and the receipt files came back together rather than one
     without the other;
   - `GET /api/inbound/log` shows the mailed-receipt archives;
   - the learned memory page is not empty (`learning.sqlite` restored).
6. **Say what was lost.** A copy is as old as its timestamp; everything
   between that stamp and the failure is gone. Name the window in the
   handover note rather than leaving it to be discovered: mail received
   in it can be re-sent by its senders, and a month closed in it has to
   be closed again.

## What is not built

- **Nothing is deleted from SharePoint.** Copies accumulate; pruning old
  ones is a manual act until somebody asks for retention.
- **No restore has been rehearsed** (see the top of this page).
- **The schedule is off.** Turning it on is `EXPENSE_RECON_BACKUP=1` plus
  a site in `EXPENSE_RECON_BACKUP_SITE`, both Fly env or secrets.
- **Snapshot retention is still five days.** Raising it is a Fly-side
  change, not a code one.
- **Nothing takes a copy before a schema change.** The deploy step in the
  README should gain a `backup --go` line once the schedule is on.

## The target, as of 2026-09-17

The app-only credential resolves `brisken.sharepoint.com:/sites/MARKETING`
and its default document library, and can list it (verified read-only the
day this shipped; the backup folder did not exist yet, which reads as an
empty folder rather than an error). Whether the copies should live on the
MARKETING site or somewhere finance-owned is the owner's call: any site
the credential can reach works, and the variable is the only thing that
changes.
