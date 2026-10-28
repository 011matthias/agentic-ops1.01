# Checkpoint: Brisken Recon Held Mail And Receipts Zip Drop

**Date:** 2026-09-27
**Status:** Held-mail diagnosed; reply to Nicolas sent; Receipts-page zip drop live on the backend (item 237), SPA prompt not pasted

---

## Summary

Answered why inbound receipt mail gets held (almost never now: 97 of the last
100 added; today's one hold was a mailed zip with an empty body), emailed the
sender his options, then built and shipped the owner's follow-up: the Receipts
page opens a dropped zip and files each receipt by its own month.

---

## What Was Done This Session

### Held-mail diagnosis (read-only)
1. Graph read of matthias.silva's mailbox: 12 distinct "Expense intake: mail held" alerts since August. 10 are from 2026-08-24, the day known-sender auto-render shipped (4 of them TEST drills); one on 2026-09-24 is `held_failed` from an OpenAI 429 ("no credits remaining"), since retried and added; one is today's.
2. Live `GET /api/inbound/log?detail=1`: `n_held` 1, 97/100 ingested 09-07..09-27; the 59 refusals are all relay probes.
3. Today's hold, 20:01 UTC "Nico - Receipts" from neumann.nicolas@outlook.com: the only attachment is `criss-card-receipt-audit-2026-09-23.zip` (13 MB, 108 PDFs plus xlsx/csv/txt/json) and the body is 2 chars. Mail skips zips by design, so the mail is `held_body_only`, and auto-render 409s on an empty body. His 19:33 mail was link-only (a Ziosk page) and read "Nothing added"; at 20:09 he resent it as a PDF (Chili's, 25 Sep, USD 22.60, added).
4. Hash check in-machine: 105 of the 108 zip PDFs are byte-identical to LIVE expense rows (Jan, May, Jun, Jul, Aug, Sep 2026). Three are missing everywhere: `CARD-080_2026-08-14_USD-134.48_SUPERMERCADO-FENIX__BENCH-047.pdf`, `CARD-086_2026-08-08_USD-37.07_SushiDuThiago__BENCH-031.pdf`, `LNKD_INVOICE_109249568269.pdf`.

### Reply to Nicolas (owner-approved send)
5. Sent via Graph `sendMail` as matthias.silva to neumann.nicolas@outlook.com only (202; in Sent Items 20:21:29Z, not a draft, no BCC): the three missing files, two ways in (email them to nicolas@expenses.brisken.com, or reply and Matthias adds them from the zip), the new alias, and the limits (PDF/JPG/PNG/WEBP, 30 files and 25 MB per mail). The owner asked for expenses@brisken.com as sender; that mailbox is outside the Graph allowlist and the Exchange access policy, and nothing records that it exists, so the owner chose matthias.silva. Logged verbatim in `context/comms-log.md`.

### Item 237: the Receipts page opens a zip (PR #1514, Fly `fc8db9cc`)
6. `intake_mail.expand_dropped_zips`, first in `route_dropped_receipts`: each dropped zip is unpacked beside itself (`NNNN-MMMM__member`) and deleted, so every member gets its own month verdict, ledger row (`from_zip`) and destination-month dedupe. A zip refused whole reads `zip-unreadable`, `zip-too-many-files` (the drop-wide total) or `zip-no-space` (disk floor), each with a `reason_label`. `service.zip_member_name` is now the one naming rule for both zip entrances.
7. Adversarial review subagent before commit: 5 defects and a cost risk found, all fixed with a test each (see backlog item 237).
8. Verified: full suite 4079 passed / 2 skipped, calibrate 0, ruff clean; `regress_check.py` turned 9 route-level tests red on the merged tree; live differential drill (below); cold Chrome drive of `/receipts`.
9. Record PR #1518 (item 237 heading + live checks). Lovable prompt `docs/lovable-receipts-drop-zip-prompt.md` handed as pasteable text; PROMPT-STATUS row added.

---

## Key Decisions Made

### Zips belong on the Receipts page, not the month upload
- **Choice:** open zips in the drop router, not steer operators to the month upload (which already opens zips).
- **Rationale:** the month upload files the whole zip into ONE month and dedupes only there. Nicolas's zip dropped into August would have skipped 30 and re-added 75 receipts that live in other months. The drop routes each file by its own date and dedupes in the destination month.

### A member that needs a month is not re-fileable from the page
- **Choice:** rows carry `from_zip`; the SPA shows "take it out of the zip and drop it on its own" instead of the month picker.
- **Rationale:** the page holds the zip, not the file; re-sending the zip with a month override files every sibling member a second time (reviewer reproduced `a.jpg` in two months).

### Live verification by a drop that can file nothing
- **Choice:** differential drill with a damaged zip and a spreadsheet-only zip, run on the old build and the new one.
- **Rationale:** it proves the route opens zips on the live machine with no month, expense or pool write. Before: both `unsupported-type`. After: `zip-unreadable` plus an opened member row with `from_zip`. 7 months before and after on both runs.

---

## What Did NOT Work (and why)

- **Advising "upload the zip through the app" before reading the code:** based on an API docstring. The owner's question ("can data really be extracted from zip files in the manual upload?") led to the code, which showed the month upload files a whole zip into one month. For Nicolas's mixed zip that would have re-added 75 receipts in the wrong month.
- **Claiming backlog item 232 at write time:** siblings took 232-236 while CI ran; PR #1514 went CONFLICTING twice (no checks run on a conflicting PR), renumbered to 237, and the squash commit on main still reads "item 232".
- **First `gh pr checks --watch` 20 s after the push:** "no checks reported"; the PR was already CONFLICTING, so no run existed to watch.
- **`pytest -n auto`:** pytest-xdist is not installed in the module env; the fallback plain run was needed (11 min).
- **A 150-character member-name cap:** exceeded Windows MAX_PATH in the deep pytest temp path; the cap is 100.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/intake_mail.py` | edit | `expand_dropped_zips`, zip reasons, `from_zip`, dotfile-safe staging |
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `zip_member_name` shared by both zip entrances |
| `automations/expense-reconciliation/tests/test_receipts_drop.py` | edit | 13 tests, section 4 |
| `automations/expense-reconciliation/docs/lovable-receipts-drop-zip-prompt.md` | new | SPA half |
| `automations/expense-reconciliation/docs/{api-contract,PROMPT-STATUS}.md` | edit | drop contract, prompt ledger row |
| `status/p1-improvement-backlog.md`, `status/p1-expense-reconciliation.md` | edit | item 237 + live record |
| `context/comms-log.md` (gitignored) | edit | Nicolas email verbatim |
| memory `project_brisken_expense_recon_mail_intake.md` | edit | how to diagnose a hold; where a zip goes |

Paths are under `workspace/clients/brisken/`.

---

## Current Status

Fly `fc8db9cc` live (healthz ok). `n_held` 1: Nicolas's zip mail, left held. `platform:` ops status unknown for brisken (no plan/ops figures in `infrastructure.yaml`). The Receipts page still filters zips out client-side until the Lovable prompt is pasted.

---

## Next Steps

1. Owner: paste `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-receipts-drop-zip-prompt.md` into Lovable, then run `tools/lovable-bundle-audit.py` for the keys the prompt's "After publish" names.
2. If Nicolas replies instead of re-sending: drop the three PDFs (not the zip) on the Receipts page; they route to August and to the LinkedIn invoice's own month.
3. Dismiss or leave the held `20260927T200153-b43534a5` archive once the three are in (a click, Criss's or the owner's).
4. Stale copy, not built: the month upload screens still say "up to 80 files" (real cap 500).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 237
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Zips (item 237)"

### Open Questions
- Does expenses@brisken.com exist as a mailbox? If the owner wants it as a sender, it needs a tenant admin (Dirk) to add it to the access-policy group, plus an owner directive to widen the allowlist.

### Working Notes
- Backlog numbers: check open PR heads as well as origin/main before claiming (`git fetch origin <head>` + grep `^### NNN\.`); a conflicting PR runs no checks at all.
- Held-mail alerts print `Error: -`; the reason lives in `/data/inbound/{archive}/meta.json` `skipped` plus the `message.eml` part walk (flyctl ssh, read-only).
- `settings.intake.aliases.nicolas` = "Nicolas Neumann" was set earlier today by a sibling (note #98).

### Reference Materials
- PRs #1514, #1518; scratch drill `zip_drill.py` and drive `drive_receipts.py` in this session's scratchpad.

---

## How to Continue

Nothing is in flight. Start from Next Steps 1-2; the backend needs no further work for item 237.

---

## Strategic Feedback

### What Worked Well This Session
- The pre-commit adversarial review found five real defects in a diff that had a green suite and a passing regress check, including the resume/disk-floor partial filing and the unfixable needs-month picker.
- The zero-write differential drill: the same request against the old and new build proves the change landed, with nothing to clean up.

### Suggestions
- Build a small `backlog_next_item` helper that reads the max `### NNN.` across origin/main AND open PR heads; this session did it by hand after losing the race, a recurrence of the 2026-09-25 item-216 row.

### System Health
- Pattern-rule noise: `warn-send-output-truncated` fired on a read-only `grep | head` over source that mentions `smtp_server.py`, and `warn-owner-publish-without-named-prompt` fired although the prompt file was named (by its module-relative path). Both look tunable.
- **Autonomy: 2 human interventions** (one factual challenge that exposed an unverified claim; one content addition to the outbound email).
