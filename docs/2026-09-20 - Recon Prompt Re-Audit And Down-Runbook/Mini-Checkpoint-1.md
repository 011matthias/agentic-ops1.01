# Mini-Checkpoint: Recon Prompt Re-Audit And Down-Runbook

**Date:** 2026-09-20
**Status:** TRACEABILITY loop closed earlier the same day; this is the tail
**Type:** mini

---

## Summary

After the loop closed, the owner published a batch of Lovable prompts and
asked which were still missing, then picked item 120's runbook third as the
next piece. Both were answered against live state rather than against the
repo's own record, and in both cases the record was wrong.

## What Was Done

**Prompt re-audit (PR #1146, merge `4e594123`).** Crawled the published
bundle, 44 chunks and 1,193 KB, following lazy route chunks through their
imports, matching each pending prompt on the API field names and i18n keys an
applied renderer has to name. **Seven of nine are live** and moved to Applied
with their evidence: `uncategorized-lines` (160), `operator-note` (155),
`error-page-lang` (130 §6), `card-accounts` (147), `memory-by-company` (M1),
`merchant-card` (M2 / 154), `no-card-evidence` (X1). **Two are not**, and
since the negative was what the owner actually asked for, both were
re-checked with looser signatures before being called absent:
`chase-section-label` (161) has no `chase.subtitle` and `chase.title` still
reads its old value; `merchant-profile` (M4) has no i18n key containing
"profile" anywhere, in either language.

**Item 160 closed by a drive, not by field names.** July's Microsoft
Corporation 718.20 now renders "1 of 2 receipt lines still needs a category:
25.20.", its category cell carrying "1 line on this receipt has no category"
over `(illegible) 25.20 · Needs a category`, and the generic sentence is gone
from the page entirely. One non-GET, the login. Its backlog heading and
status row said "not pasted" and are corrected.

**Item 120's runbook third (PR #1148).** `docs/if-it-is-down.md`: the three
independent checks (API `/healthz` with its disk block, the port-25 MX
banner, the SPA), the `FLY_API_TOKEN` export that works around `flyctl`
answering "no access token available" while the token is valid, the three
failure shapes including the 2026-09-10 wedged machine with its real recovery
(destroy, `volumes fork`, redeploy, which is where `recon_data_v2` came
from), deploying only from a detached `origin/main` worktree, rolling back by
image, and a call-it-up check that refuses `/healthz` alone. Every value read
off the live app; every command verified against `flyctl` before being
written down. `backup-and-restore.md` gains a pointer, so **down** is the new
document and **lost** is the old one.

## What Did NOT Work (and why)

- **Answering "which prompts are missing" from PROMPT-STATUS.md:** the
  Not-applied table was wrong in seven of its nine rows, because the owner
  had published and nothing had re-audited since. The file's own opening rule
  ("a prompt's presence in `docs/` says nothing about whether it was ever
  pasted") is what caught it. Only a bundle crawl answers that question.
- **Closing item 160 on the bundle carrying its four i18n keys:** bundle
  strings are not a render. Their presence proves the paste landed, not that
  the row shows anything. The drive also proved the negative half, that the
  old sentence is gone from the page, which no grep could have shown.
- **Offering item 120 to the owner as one of several things we could do:**
  the B1 stop-gate blocked the message, correctly. The item splits three ways
  and only one third needed a decision: the hosting-org move needs Dirk and
  money, a rehearsed restore is a live-volume action, and the runbook needed
  neither. The read-only half (enumerating what recovery docs already exist)
  was mine to take first, and the remainder belonged in `AskUserQuestion`
  with a recommendation.

## Current Status

Live is **Fly v193**; nothing merged is undeployed. This checkpoint's
own entry is session **10**: a sibling's "Statement Fill-Colour
Classifier Findings" landed as 9 while this one was being written, so
mine moved after theirs rather than renumbering a row already on `main`.
PR #1148 merged on green; nothing is in flight but this checkpoint. Next free backlog number is **162**; next free Shipped
iteration is **109** (108 = the runbook).

**Five shipped features are inert on missing owner-side data**, all read off
the live app on 2026-09-20 rather than from documents:

| Item | Live state |
|---|---|
| 147 card accounts | 0 of 9 cards carry a `parent` |
| 118 cost centres | `cost_centers` is `{}` |
| M4 merchant profiles | 0 of 28 merchants carry one |
| 108 statements | 5 of 9 cards have never had a statement loaded in any month: `card-0113`, `card-1176`, `card-6013`, `card-8311`, `card-9693` |
| 119 backup | `EXPENSE_RECON_BACKUP` is not among the app's nine secrets |

Item 108 is the heaviest: the Cloud Services and Consulting card spend cannot
reconcile at all. Item 119 is the cheapest to fix and the most dangerous to
leave: the only copies of Criss's data are the live volume and Fly's 5-day
snapshots, both inside the developer's **personal** Fly account
(`flyctl status` prints `Owner: personal`).

## Next Steps

1. **Owner:** paste `lovable-chase-section-label-prompt.md` (161) and
   `lovable-merchant-profile-prompt.md` (M4). Both were handed over as
   pasteable text; re-audit and drive April afterwards.
2. **Owner:** set `EXPENSE_RECON_BACKUP=1`. One secret, and it is the whole
   of Brisken's independent copy.
3. **Owner:** the four data gaps above, in the order of the table.
4. Item 120's open two thirds stay open and are not the agent's: the
   hosting-organisation move, and a rehearsed restore.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/if-it-is-down.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
  (Not applied is down to two, with the 2026-09-20 audit note)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 120 and
  160, Shipped rows 106 to 108)
