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
itself holds. **It is on since 2026-09-21** (owner directive), writing to
the `ExpenseTool` folder the owner created on the MARKETING site. The first
copy is `expense-recon-data-20260921T181135Z.zip`, 127.2 MB, taken 42
seconds after the restart that switched it on.

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
| `EXPENSE_RECON_BACKUP_MAX_BYTES` | refuse above this size (default 100 MB). **Set to 400 MB on 2026-09-21**, because the data folder had already passed the default: 146 MB on the volume, and the first archive alone was 127.2 MB. Left at the default, the schedule would have started and refused every run |

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
- ~~The schedule is off.~~ On since 2026-09-21, daily. Turning it on took
  three settings, not the one this line implied: without
  `EXPENSE_RECON_BACKUP_MAX_BYTES` raised, `run_backup` refuses on the size
  ceiling before it ever reaches SharePoint, so the schedule would have run
  and copied nothing while reading as enabled. Anyone reusing this on
  another volume should check the folder size against the ceiling FIRST.
- **Snapshot retention is still five days.** Raising it is a Fly-side
  change, not a code one.
- **Nothing takes a copy before a schema change.** The deploy step in the
  README should gain a `backup --go` line once the schedule is on.

## The target, as of 2026-09-21

`brisken.sharepoint.com:/sites/MARKETING`, folder **`ExpenseTool`**, which
the owner created and named on 2026-09-21. App-only throughout: the
credential resolves the site, resolves the default document library
(`Documents`), lists 18 root folders and writes into `ExpenseTool`. No
delegated token is involved, which retires the workaround
`rule_brisken_graph_first` still described.

One trap worth naming, because it cost a false alarm while this was being
checked. `list_folder` turns any Graph 404 into `[]`, so `backup --check`
prints "0 file(s)" both for an empty folder and for a folder that is not
there, and the same swallow covers a 404 raised while resolving the drive.
That is the right behaviour for a first run, but it means a "0 files"
answer is not by itself evidence that the target is reachable. Prove the
instrument before believing it: list the drive root and confirm it returns
folders you recognise. It did, which is why the empty answer here was read
as a genuinely empty folder rather than as a broken credential.
