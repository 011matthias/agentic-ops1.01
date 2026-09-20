# If it is down, do this (backlog item 120)

For whoever is holding this when the usual developer is not. Every command
and every value below was read from the live app on 2026-09-20, not copied
from an older document. Work top to bottom; stop as soon as it answers.

**Read the limits at the bottom before you trust this in an emergency.**
Two of them change what you can actually do.

## 0. What you need before you start

| You need | Where it is | Without it |
|---|---|---|
| A Fly token with access to `brisken-expense-recon` | `~/.fly/config.yml` on the developer's machine, key `access_token` | you can read nothing and restart nothing |
| The operator code | Fly secret `EXPENSE_RECON_OPERATOR_CODE`; a copy is in the gitignored `workspace/clients/brisken/context/.env` | you can reach `/healthz` but not log in |
| This repository | `011matthias/agentic-ops1.01` | you cannot redeploy |

**`flyctl` on the developer's Windows box answers "no access token available"
for every command even when the token is valid.** `flyctl auth login` is not
the fix. Read the token out of the file and export it:

```bash
export FLY_API_TOKEN=$(grep -oP '(?<=access_token: ).*' ~/.fly/config.yml | tr -d '"'"'"' \r')
```

## 1. Is it actually down, and which half

Three independent things can fail. Check all three before you touch
anything; the fix differs per shape.

```bash
# 1. the API. Expect {"status":"ok", ...} with disk.available true
curl -s --max-time 25 https://brisken-expense-recon.fly.dev/healthz

# 2. the mailbox. Expect a 220 banner. This is the MX for
#    expenses.brisken.com; if it is dead, receipts silently stop arriving
#    and nobody is told
printf 'QUIT\r\n' | timeout 20 nc expenses.brisken.com 25

# 3. the screen Criss uses
curl -s -o /dev/null -w '%{http_code}\n' --max-time 25 https://expenses.brisken.com
```

`/healthz` also carries the disk. `disk.intake_refusing: true` means the
volume crossed its floor (200 MB) and the mailbox is refusing new mail to
protect the database. That is section 4, not section 3.

The same three checks run every 10 minutes from GitHub Actions
(`tools/recon_uptime_probe.py`), which opens one `recon-uptime` issue and
sends one mail per outage. If you are reading this because of that issue,
the checks above are the ones that fired.

## 2. The app in one paragraph

One Fly machine, `7843d54b579598`, in Frankfurt, app
`brisken-expense-recon`. It serves the API on 8080 and the mail listener on
2525, published as public port 25 off a dedicated IPv4. Data lives on the
volume `recon_data_v2` (`vol_vgnplk8909y0q184`, zone 778b) mounted at
`/data`: the run database, every stored receipt, and the mail archive.
**Both services are pinned always-on and must stay that way** (see the
limit in section 7). The UI is a separate Lovable app at
expenses.brisken.com that talks to this API; if the UI is blank but
`/healthz` is fine, the fault is the UI, not this app.

## 3. Shape A, the process is dead but the machine is fine

`/healthz` times out or 502s; `flyctl status` shows the machine `started`.

Fly's own healthcheck restarts a dead process on its own within about a
minute, so wait one minute and re-check first. If it does not come back:

```bash
MSYS_NO_PATHCONV=1 flyctl status -a brisken-expense-recon
MSYS_NO_PATHCONV=1 flyctl logs -a brisken-expense-recon           # the reason
MSYS_NO_PATHCONV=1 flyctl machine restart 7843d54b579598 -a brisken-expense-recon
```

Re-run section 1. If the process dies again straight after the restart, the
build is bad: go to section 6.

## 4. Shape B, the disk is full

`/healthz` answers, `disk.available` is false or `disk.intake_refusing` is
true. The volume is 1 GB. Mail is being refused on purpose; nothing is lost
at the sender's end yet, but it will start bouncing.

```bash
MSYS_NO_PATHCONV=1 flyctl ssh console -a brisken-expense-recon --pty=false -C "sh -c 'df -h /data; du -sh /data/* | sort -h | tail -10'"
```

The usual culprit is `/data/inbound` (the mail archive) or the extraction
cache at `/data/extraction-cache.sqlite`. **The cache is safe to delete**;
it only makes the next reading of an already-seen document cost money again.
The archive and the run database are not safe to delete. If neither frees
enough, grow the volume (`flyctl volumes extend`) rather than deleting
records.

## 5. Shape C, the machine is wedged (the 2026-09-10 outage)

This one has happened. The machine auto-stopped cleanly, then wedged in
flyd: it reported `stopped` when signalled and `active` when started, so
every proxy auto-start was refused, and the UI and the MX both 502'd for
about 50 minutes until the owner noticed. The cause underneath was that the
host holding the volume had run out of capacity, so a restart could never
have worked. Recovery was:

1. destroy the machine,
2. `flyctl volumes fork` the volume onto a fresh host,
3. redeploy the identical image against the forked volume.

That is where `recon_data_v2` came from. `recon_data`
(`vol_4m3p65dn1nqkowzv`) is the unattached copy from that day and is still
there as a rollback.

**Do this only when a restart has already failed and the logs show the
machine never came up**, because it destroys the machine. The volume, and
therefore the data, survives the fork.

## 6. Redeploying, from the repository alone

Deploy only from a clean checkout of `origin/main`, never from a feature
branch: the deploy ships the working tree it is pointed at, and `fly.toml`
from a stale branch would silently undo the platform settings.

```bash
git -C <repo> fetch origin
git -C <repo> worktree add --detach <somewhere-new> origin/main
# confirm the commit you mean is there
git -C <somewhere-new> log --oneline -1

M=<somewhere-new>/workspace/clients/brisken/automations/expense-reconciliation
MSYS_NO_PATHCONV=1 flyctl deploy "$M" --config "$M/fly.toml" \
  -a brisken-expense-recon --remote-only
```

**To roll back to a release that worked**, take its image from the release
list and deploy that image rather than rebuilding:

```bash
MSYS_NO_PATHCONV=1 flyctl releases -a brisken-expense-recon --image
MSYS_NO_PATHCONV=1 flyctl deploy -a brisken-expense-recon \
  -i registry.fly.io/brisken-expense-recon:deployment-<ID-from-that-list>
```

Rolling back the image does not roll back the data on the volume.

## 7. Calling it back up

Do not call it fixed on `/healthz` alone. Run all three checks from section
1, then open expenses.brisken.com, log in with the operator code, and open
one month. The API answering and the screen working are different claims,
and the one Criss cares about is the second.

If the outage was shape C, also confirm `flyctl status` shows one machine
`started` with its check passing, and that `fly.toml` still reads
`auto_stop_machines = false` on **both** services. Restoring scale-to-zero
is what put the mailbox behind an auto-start that could fail; it is the one
setting never to "tidy up".

## 8. The limits of this document, stated plainly

Three of these change what a stand-in can actually do, and none of them is
fixable from the repository:

1. **The app runs under the developer's PERSONAL Fly account**
   (`flyctl status` prints `Owner: personal`). No organisation token exists.
   If that account is unreachable, nothing in this document works, and
   nobody at Brisken can restart the tool. This is the substance of backlog
   item 120 and it needs a hosting organisation Brisken pays for, with Dirk
   as an admin.
2. **The only Brisken-held copy of the data is switched off.** The
   SharePoint backup is built (`docs/backup-and-restore.md`) but
   `EXPENSE_RECON_BACKUP` is not among the app's secrets, verified
   2026-09-20, so the schedule never starts. The copies that do exist are
   the live volume and Fly's own 5-day snapshots, both inside that same
   personal account. Turning it on is one secret.
3. **No restore has ever been rehearsed.** `docs/backup-and-restore.md`
   says so in its own opening line. The restore path is written down and
   has never been run, so treat section 5 and any restore as a first
   attempt, not a drill.

What this document does cover, and what item 120 asked for third, is the
part that needed no decision from anybody: if it is down, a person holding
the token and this repository can now tell which half is down, fix the two
recoverable shapes, redeploy or roll back, and know what to check before
saying it is back.
