# Operating this thing

For a stand-in with repository access and no context, on a day when the
app is **working**. If it is not working, `docs/if-it-is-down.md` is the
page for that, and this one deliberately does not repeat it.

Everything below was run against the live app on 2026-09-20 unless a line
says otherwise. **Verified against commit `603b4d1d`.**

## What you need first

The three things in `docs/if-it-is-down.md` section 0: a Fly token, the
operator code, this repository.

```bash
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
API=https://brisken-expense-recon.fly.dev
```

**Which host needs that User-Agent, and which does not.** The two halves
sit behind different front doors, and the difference will otherwise cost
you a wrong diagnosis:

| Host | Served by | Plain `urllib`, no UA |
|---|---|---|
| `brisken-expense-recon.fly.dev` (the API) | Fly | **200.** No UA needed |
| `expenses.brisken.com` (the screen) | Cloudflare | **403.** A browser UA is required |

Measured on 2026-09-20 by sending the same request to each host with and
without a browser UA. So a script that reads the API needs no disguise,
and a script that touches the SPA host does; a 403 from
`expenses.brisken.com` with no UA set is your own tool, not an outage.
The commands below set `$UA` throughout anyway, because it is harmless on
the API and necessary the moment you point the same shell at the SPA.

Log in once and keep the token in a variable. The operator code is a Fly
secret (`EXPENSE_RECON_OPERATOR_CODE`) with a copy in the gitignored
`workspace/clients/brisken/context/.env`. Never echo either one.

```bash
CODE=$(grep -oP '(?<=^EXPENSE_RECON_OPERATOR_CODE=).*' \
        workspace/clients/brisken/context/.env | tr -d '\r"')
TOK=$(curl -s -A "$UA" -H 'Content-Type: application/json' \
        -d "{\"code\":\"$CODE\"}" "$API/api/login" \
      | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
AUTH="Authorization: Bearer $TOK"
```

A good result is a token string. A bad one is `{"error":"invalid code"}`,
which means the code you read is not the code deployed; compare the Fly
secret's digest with `flyctl secrets list` rather than guessing.

**One read to never do: `GET /runs/{id}/expense-report.pdf`.** It writes
render outcomes back into the run, so it is not a read at all. Every other
`GET` on this page is safe on Criss's live months.

## Read live state

One endpoint answers "what is this app doing right now":

```bash
curl -s -A "$UA" -H "$AUTH" "$API/api/operator/state" | python -m json.tool
```

It returns `operator_runs` (every month in the store), `published_runs`,
`intakes`, `processing` (pipeline work in flight), `rematches`,
`rematch_pending`, and `feedback.count`.

What it looked like on 2026-09-20, so you have a baseline to compare
against: **7 months** (April, January, June, May, September, August,
July 2026), **0 published**, **0 processing**, **36 rematch events**, **0
pending**, **72 feedback notes**.

`processing` being non-empty means a pipeline is mid-flight; that is
normal for a few minutes after an upload and abnormal for an hour.

Two other reads worth knowing:

```bash
# Criss's own notes, newest last. Read this FIRST when she reports anything.
curl -s -A "$UA" -H "$AUTH" "$API/feedback.jsonl" | tail -5

# What arrived in the mailbox, and what was held rather than filed
curl -s -A "$UA" -H "$AUTH" "$API/api/inbound/log" | python -m json.tool | head -40
```

And the health of the process itself, which needs no token:

```bash
curl -s -A "$UA" "$API/healthz" | python -m json.tool
```

## Deploy

`docs/if-it-is-down.md` section 6 has the emergency version and the two
warnings that matter (deploy only from a clean detached `origin/main`
worktree, because the deploy ships the `fly.toml` it is pointed at). This
is the same command with the build stamp, which is what makes the deploy
verifiable afterwards:

```bash
git -C <repo> fetch origin
git -C <repo> worktree add --detach <new-dir> origin/main
M=<new-dir>/workspace/clients/brisken/automations/expense-reconciliation

# Refuse to deploy a dirty tree: the commit you stamp would not describe
# what you ship. (Verified: fires on a dirty module, silent on a clean one.)
git -C "$M" diff --quiet HEAD -- . || { echo "dirty tree, stop"; exit 1; }

COMMIT=$(git -C "$M" rev-parse HEAD)
MSYS_NO_PATHCONV=1 flyctl deploy "$M" --config "$M/fly.toml" \
  -a brisken-expense-recon --remote-only \
  --build-arg GIT_COMMIT="$COMMIT"
```

**Then prove it is the thing you shipped**, which is the whole point of
the stamp:

```bash
curl -s -A "$UA" "$API/healthz" | python -m json.tool | grep -E 'commit|image'
# `commit` must equal $COMMIT.
```

A good result is your commit. A **blank** `commit` means the deploy ran
without `--build-arg`; the app is fine, but it can no longer tell you what
it is, so redeploy with the flag. A **different** commit means someone
else deployed after you.

Do not stop at `/healthz`. Open expenses.brisken.com, log in, open one
month: the API answering and the screen working are different claims.

## Roll back

`flyctl releases --image` lists the images; deploy one by reference rather
than rebuilding (`docs/if-it-is-down.md` section 6 has the command).

Two things to hold on to. Rolling back the image does **not** roll back
the data on the volume. And after a rollback `/healthz` reports the commit
of the image you rolled back TO, which is the correct answer and will not
match your local `HEAD`; that disagreement is the rollback working, not a
fault.

## Audit a publish

Publishing a month is its sign-off: the route refuses a month that is not
complete unless the caller passes `{"override": true}`, and it never
publishes a classic run.

What is recorded, on the run itself:

| Field | Means |
|---|---|
| `published` | whether it is signed off right now |
| `published_at` | when |
| `published_by` | the operator LABEL of whoever did it (see the next section) |
| `published_override` | true if it was published while incomplete |

Read them for one month with `GET /api/runs/{run_id}`, or across all of
them in `published_runs` from `/api/operator/state`.

**Two limits, both real, both worth knowing before you rely on this.**

*There is no publish log.* Those four fields are current state, not
history. Unpublishing deliberately clears `published_by`,
`published_at` and `published_override` so the row describes only the
current sign-off, and a publish writes no entry to the decision-history
table. So a publish, unpublish, republish sequence leaves no trace of the
first one, and "who published this in August" is unanswerable once it has
been unpublished. The durable per-row trail
(`GET /api/runs/{run_id}/history`) covers Criss's decisions on individual
charges, with triggers `statement`, `receipts`, `reread`, `cards`,
`master_data`, `month_move`, `set_aside`, `trip` and `resume`. Publishing
is not among them.

*No month has ever been published.* `published_runs` was empty on
2026-09-20 across all 7 months. So everything in this section is read from
the code, not from a publish anybody has watched happen, and the first
real one should be checked rather than assumed.

## Where the labels live

Every login gets the same operator role; a **label** is what makes an
action attributable and lets one person's access be removed without
rotating everyone else's. The label rides inside the signed token and is
what lands in `published_by` and in the feedback notes.

Two secrets, both on Fly, both deployed today:

| Secret | What it holds |
|---|---|
| `EXPENSE_RECON_OPERATOR_CODES` | comma-separated `code:label` pairs; labels are lowercase `[a-z0-9_-]`, and a code may contain neither `:` nor `,` |
| `EXPENSE_RECON_OPERATOR_CODE` | the older single shared code, label `operator`; still honoured |

A third, `EXPENSE_RECON_AUTH_SECRET`, signs the tokens. It is set in
production on purpose: without it the app falls back to a per-process
random key and everybody is logged out on every restart.

To add or remove a person you rewrite the whole `..._CODES` value
(`flyctl secrets set`), which restarts the app. Read the current labels
off a month's `published_by` or the feedback notes rather than trying to
recover them from the secret, which prints only a digest.

The code in `context/.env` is the shared one. If you find yourself wanting
a personal label, that is the right instinct: attribution on a shared code
says `operator` and names nobody.

## Where the notifier lives, and why that is a problem

Every alert the tool raises is sent by a script on the developer's Windows
laptop, not by the app. The app holds no Graph credential and never sends
mail; `tools/brisken-recon-notify.py` polls `/api/operator/state`, diffs it
against a local state file, and sends via Microsoft Graph.

Verified on 2026-09-21:

| | |
|---|---|
| Task | `BriskenReconNotify`, state Ready |
| Every | 15 minutes (`PT15M`) |
| Runs | `tools/brisken-recon-notify-run.py --once` |
| Runs from | `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-notify` |

It sends on: a new operator run, a new intake, a newly published run, new
reviewer feedback, and each living-month re-match event.

**It has its own clone, which fast-forwards itself before every run**
(2026-09-21). Until then it ran from the shared working tree, which nothing
updates automatically, so the code it executed was whatever that tree
happened to hold. That did cost something: item 113 added re-match FAILURE
alerts to the notifier and landed on `main` at 2026-09-17 17:10, the shared
tree's next pull was 2026-09-21 10:19, and for the 89 hours between them
the task ran a notifier with no `diff_rematch_failures` in it. A whole
alarm class, shipped and green in CI, absent from the only path that mails
anybody, with nothing to notice it.

Reading the freshness, when the notifier does something odd:

```bash
tail -3 /c/Users/neuma_p1qrsic/Repo/agentic-ops1/.scratch/recon-notify-runs.log
# 2026-09-21T19:47:02Z commit=aa2980f9 update=Already up to date. exit=0
```

`update=STALE (...)` means the fast-forward failed and the run went ahead
on the commit named, which is the intended order: running slightly stale
beats not running. A missing `.env` is the one fatal case and exits
non-zero, so it shows up as a non-zero `LastTaskResult` rather than as a
quiet day. The clone shares no `.git` with the shared tree and the runner
issues no git command against it, so neither can move the other.

The larger point, which is backlog item 121 rather than this page: if that
laptop is off, no alarm reaches anybody, and nothing in the app notices.
Held-mail alerts go to Criss and Matthias (set 2026-09-17); the feedback,
re-match and publish pings still go to Matthias alone.

## What this page cannot give you

The same two limits `docs/if-it-is-down.md` ends on, because they are
properties of the arrangement rather than of the documentation:

1. The app runs under the developer's **personal** Fly account
   (`flyctl status` prints `Owner: personal`). Everything here works for
   someone holding that token, and for nobody at Brisken independently.
2. The SharePoint backup exists in code but has never been switched on:
   `EXPENSE_RECON_BACKUP` was still absent from the nine deployed secrets
   when this was checked on 2026-09-20. The only copies are the live
   volume and Fly's 5-day snapshots, both inside that same account.

Both are owner decisions tied to the October arrangement, not tasks.

Related: `docs/if-it-is-down.md`, `docs/backup-and-restore.md`,
`docs/screen-field-map.md`, `docs/api-contract.md`.
